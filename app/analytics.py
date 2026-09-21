from datetime import datetime, timezone
import logging

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as postgres_insert

from app.database import SessionLocal
from app.models import PageViewDaily

logger = logging.getLogger(__name__)
PAGE_ROUTES = {"read_root", "tools_list", "tools_detail", "services_page", "about_page", "guide_page", "news_list", "news_detail", "contact_page"}


def record_page_view(path: str):
    try:
        with SessionLocal() as db:
            insert = postgres_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
            statement = insert(PageViewDaily).values(day=datetime.now(timezone.utc).date(), path=path, views=1)
            statement = statement.on_conflict_do_update(
                index_elements=[PageViewDaily.day, PageViewDaily.path],
                set_={"views": PageViewDaily.views + 1},
            )
            db.execute(statement)
            db.commit()
    except Exception:
        # A metrics failure must not prevent the visitor from reading the site.
        logger.exception("Unable to record page view")
