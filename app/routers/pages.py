from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import News

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="templates")


@router.get("/services", response_class=HTMLResponse)
def services_page(request: Request):
    return templates.TemplateResponse("services.html", {"request": request})


@router.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@router.get("/guide", response_class=HTMLResponse)
def guide_page(request: Request):
    return templates.TemplateResponse("guide.html", {"request": request})


@router.get("/news", response_class=HTMLResponse)
def news_list(request: Request, q: str = "", page: int = Query(1, ge=1), db: Session = Depends(get_db)):
    q = q.strip()
    query = db.query(News).filter(News.status == "published")
    if q:
        query = query.filter(or_(News.title.icontains(q, autoescape=True), News.summary.icontains(q, autoescape=True)))
    total = query.count()
    page_count = max(1, (total + 8) // 9)
    page = min(page, page_count)
    articles = query.order_by(News.published_at.desc(), News.id.desc()).offset((page - 1) * 9).limit(9).all()
    return templates.TemplateResponse("news/index.html", {"request": request, "articles": articles, "q": q,
        "total": total, "page": page, "page_count": page_count})


@router.get("/news/{slug}", response_class=HTMLResponse)
def news_detail(request: Request, slug: str, db: Session = Depends(get_db)):
    article = db.query(News).filter(News.slug == slug, News.status == "published").first()
    if article is None:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return templates.TemplateResponse("news/detail.html", {"request": request, "article": article})
