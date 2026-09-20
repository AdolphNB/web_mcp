from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import News, NewsAudit, PageViewDaily
from app.security import management_role, require_editor

router = APIRouter(prefix="/api/admin", tags=["网站管理"])


class NewsBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=50000, description="纯文本正文，保留换行，不执行 HTML")
    source_url: HttpUrl | None = Field(default=None, max_length=2000)
    status: Literal["draft", "published"] = "draft"


class NewsCreate(NewsBody):
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class NewsUpdate(NewsBody):
    expected_version: int = Field(ge=1, description="从读取接口取得的版本；版本冲突时重新读取")


class NewsResponse(NewsCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    version: int
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


@router.get("/analytics", dependencies=[Depends(management_role)])
def analytics(days: int = Query(7, ge=1, le=90), db: Session = Depends(get_db)):
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days - 1)
    query = db.query(PageViewDaily).filter(PageViewDaily.day >= start, PageViewDaily.day <= today)
    daily = dict(query.with_entities(PageViewDaily.day, func.sum(PageViewDaily.views)).group_by(PageViewDaily.day).all())
    pages = query.with_entities(PageViewDaily.path, func.sum(PageViewDaily.views).label("views"))
    pages = pages.group_by(PageViewDaily.path).order_by(func.sum(PageViewDaily.views).desc(), PageViewDaily.path).limit(20).all()
    return {
        "metric": "page_views", "timezone": "UTC", "days": days,
        "start_date": start, "end_date": today, "total_views": sum(daily.values()),
        "daily": [{"date": start + timedelta(days=i), "views": daily.get(start + timedelta(days=i), 0)} for i in range(days)],
        "top_pages": [{"path": path, "views": views} for path, views in pages],
        "note": "成功页面 GET 请求数（PV），不是独立访客；排除 API、静态资源、预取和常见爬虫。从启用后开始计数。",
    }


@router.get("/news", dependencies=[Depends(require_editor)])
def list_news(status: Literal["draft", "published"] | None = None, offset: int = Query(0, ge=0),
              limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    query = db.query(News)
    if status:
        query = query.filter(News.status == status)
    return {"total": query.count(), "items": [NewsResponse.model_validate(item) for item in query.order_by(News.updated_at.desc(), News.id.desc()).offset(offset).limit(limit).all()]}


def get_article(db, slug):
    article = db.query(News).filter(News.slug == slug).first()
    if not article:
        raise HTTPException(404, "News not found")
    return article


@router.get("/news/{slug}", response_model=NewsResponse, dependencies=[Depends(require_editor)])
def read_news(slug: str, db: Session = Depends(get_db)):
    return get_article(db, slug)


@router.post("/news", response_model=NewsResponse, status_code=201, dependencies=[Depends(require_editor)])
def create_news(payload: NewsCreate, db: Session = Depends(get_db)):
    values = payload.model_dump(mode="json")
    article = News(**values, version=1, published_at=datetime.now(timezone.utc) if payload.status == "published" else None)
    db.add(article)
    db.add(NewsAudit(slug=payload.slug, action="publish" if payload.status == "published" else "create", version=1))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Slug already exists; read the existing article before retrying")
    db.refresh(article)
    return article


@router.put("/news/{slug}", response_model=NewsResponse, dependencies=[Depends(require_editor)])
def update_news(slug: str, payload: NewsUpdate, db: Session = Depends(get_db)):
    article = get_article(db, slug)
    action = "update"
    if article.status != payload.status:
        action = "publish" if payload.status == "published" else "unpublish"
    values = payload.model_dump(mode="json", exclude={"expected_version"})
    values.update(version=payload.expected_version + 1, updated_at=datetime.now(timezone.utc))
    if payload.status == "published" and article.published_at is None:
        values["published_at"] = datetime.now(timezone.utc)
    result = db.execute(update(News).where(News.slug == slug, News.version == payload.expected_version).values(**values))
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Version conflict; read the latest article before updating")
    db.add(NewsAudit(slug=slug, action=action, version=payload.expected_version + 1))
    db.commit()
    db.refresh(article)
    return article


@router.get("/audit", dependencies=[Depends(require_editor)])
def audit(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    return [{"slug": row.slug, "action": row.action, "version": row.version, "created_at": row.created_at}
            for row in db.query(NewsAudit).order_by(NewsAudit.id.desc()).limit(limit).all()]
