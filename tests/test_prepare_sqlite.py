from pathlib import Path
import sqlite3

from dotenv import dotenv_values
import pytest
from sqlalchemy.engine import make_url

from scripts.prepare_sqlite import prepare_sqlite


def test_relocation_preserves_wal_data_and_is_idempotent(tmp_path):
    project, data = tmp_path / "site", tmp_path / "data"
    project.mkdir()
    env = project / ".env"
    env.write_text("DATABASE_URL=sqlite:///./mcptools.db\nSITE_ADMIN_TOKEN=unchanged\nLITERAL=$(touch should-not-exist)\n")
    source = project / "mcptools.db"
    # Leave connection open to ensure the committed data still lives in the WAL.
    with sqlite3.connect(source) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE example (value TEXT)")
        db.execute("INSERT INTO example VALUES ('original')")
        db.commit()
        assert prepare_sqlite(project, data)
        destination = Path(make_url(dotenv_values(env)["DATABASE_URL"]).database)
        with sqlite3.connect(destination) as copied:
            assert copied.execute("SELECT value FROM example").fetchall() == [("original",)]
        assert db.execute("SELECT value FROM example").fetchall() == [("original",)]
    assert dotenv_values(env)["SITE_ADMIN_TOKEN"] == "unchanged"
    assert dotenv_values(env)["LITERAL"] == "$(touch should-not-exist)"
    assert not prepare_sqlite(project, data)
    assert source.exists()


@pytest.mark.parametrize("url", ["postgresql://user:password@localhost/site", "sqlite:///:memory:"])
def test_external_database_configuration_is_unchanged(tmp_path, url):
    env = tmp_path / ".env"
    env.write_text("DATABASE_URL=" + url)
    assert not prepare_sqlite(tmp_path, tmp_path.parent / "external-data")
    assert env.read_text() == "DATABASE_URL=" + url


def test_existing_destination_is_never_overwritten(tmp_path):
    project, data = tmp_path / "site", tmp_path / "data"
    project.mkdir()
    data.mkdir()
    env = project / ".env"
    env.write_text("DATABASE_URL=sqlite:///./mcptools.db")
    destination = data / "mcptools.db"
    destination.write_text("existing data")
    with pytest.raises(FileExistsError):
        prepare_sqlite(project, data)
    assert destination.read_text() == "existing data"
    assert env.read_text() == "DATABASE_URL=sqlite:///./mcptools.db"


def test_new_install_points_to_separate_data_directory(tmp_path):
    project, data = tmp_path / "site", tmp_path / "data"
    project.mkdir()
    (project / ".env").write_text("DEBUG=False\n")
    assert prepare_sqlite(project, data)
    url = make_url(dotenv_values(project / ".env")["DATABASE_URL"])
    assert Path(url.database) == data / "mcptools.db"


def test_data_directory_cannot_be_inside_application(tmp_path):
    with pytest.raises(ValueError, match="outside"):
        prepare_sqlite(tmp_path, tmp_path / "data")
