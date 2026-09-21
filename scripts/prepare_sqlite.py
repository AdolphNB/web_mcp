"""Relocate an in-project SQLite database before making application code read-only.

Run during a maintenance window with application workers stopped. The original
database stays intact. External databases and SQLite files outside the checkout
are left alone. This reads dotenv data; it never executes shell configuration.
"""
import argparse
from contextlib import closing
from pathlib import Path
import sqlite3

from dotenv import dotenv_values, set_key
from sqlalchemy.engine import make_url


def prepare_sqlite(project: Path, data_dir: Path):
    project, data_dir = project.resolve(), data_dir.resolve()
    if data_dir == project or project in data_dir.parents:
        raise ValueError("The data directory must be outside the application directory")
    env_file = project / ".env"
    values = dotenv_values(env_file)
    url = make_url(values.get("DATABASE_URL") or "sqlite:///./mcptools.db")
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        return False
    if url.query.get("uri") == "true":
        raise ValueError("Move SQLite URI databases manually before hardening permissions")
    source = Path(url.database)
    source = (project / source).resolve() if not source.is_absolute() else source.resolve()
    if project not in source.parents:
        return False
    data_dir.mkdir(parents=True, exist_ok=True)
    destination = data_dir / source.name
    pending = data_dir / (source.name + ".pending")
    if destination.exists() or pending.exists():
        raise FileExistsError("SQLite destination already exists; inspect it before retrying. No files replaced.")
    if source.exists():
        # SQLite backup includes committed WAL content; raw file copying does not.
        try:
            with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as old:
                with closing(sqlite3.connect(pending)) as new:
                    old.backup(new)
                    if new.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                        raise RuntimeError("SQLite backup integrity check failed")
            pending.replace(destination)
        except Exception:
            pending.unlink(missing_ok=True)
            raise
    new_url = url.set(database=destination.as_posix()).render_as_string(hide_password=False)
    set_key(env_file, "DATABASE_URL", new_url)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    changed = prepare_sqlite(args.project, args.data_dir)
    print("SQLite configuration relocated; original database retained." if changed else "Database location unchanged.")
