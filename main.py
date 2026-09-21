from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models import Tool, News
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse, HTMLResponse
from app.http_security import ScopedCORSMiddleware, SecurityHeadersMiddleware, SECURITY_HEADERS
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routers import tools
from app.routers import seo
from app.routers import management, pages, support
from app.middleware import log_api_call

app = FastAPI(
    title="singularitynear.com API",
    description="基础 FastAPI 应用，包含 CORS 和简单错误处理",
    version="0.1.0",
)

app.add_middleware(ScopedCORSMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Configure Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/res", StaticFiles(directory="res"), name="res")

# Add API logging middleware
app.middleware("http")(log_api_call)
# Include routers
app.include_router(tools.router, prefix="/api")
app.include_router(seo.router)
app.include_router(management.router)
app.include_router(pages.router)
app.include_router(support.router)


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request, db: Session = Depends(get_db)):
    """公司首页"""
    latest_news = db.query(News).filter(News.status == "published").order_by(News.published_at.desc(), News.id.desc()).limit(3).all()
    return templates.TemplateResponse("index.html", {"request": request, "latest_news": latest_news})


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


@app.get("/tools", response_class=HTMLResponse)
def tools_list(request: Request, q: str = "", category: str = "", db: Session = Depends(get_db)):
    """工具列表页面"""
    q = q.strip()
    category = category.strip()
    query = db.query(Tool).filter(Tool.is_active == True)
    total = query.count()
    categories = [row[0] for row in query.with_entities(Tool.category).distinct()
                  .order_by(Tool.category).all() if row[0]]
    if q:
        query = query.filter(or_(Tool.name.icontains(q, autoescape=True),
                                 Tool.short_description.icontains(q, autoescape=True),
                                 Tool.description.icontains(q, autoescape=True)))
    if category:
        query = query.filter(Tool.category == category)
    return templates.TemplateResponse("tools/index.html", {
        "request": request, "tools": query.order_by(Tool.name, Tool.id).all(),
        "q": q, "category": category, "categories": categories, "total": total,
    })


@app.get("/tools/{slug}", response_class=HTMLResponse)
def tools_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    """工具详情页面"""
    tool = db.query(Tool).filter(Tool.slug == slug, Tool.is_active == True).first()
    if tool is None:
        return templates.TemplateResponse(
            "404.html", {"request": request}, status_code=404
        )
    return templates.TemplateResponse(
        "tools/detail.html", {"request": request, "tool": tool}
    )


@app.exception_handler(StarletteHTTPException)
async def page_not_found(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and "text/html" in request.headers.get("accept", "") and not request.url.path.startswith("/api/"):
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return await http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Basic error handler, do not leak internal details in production
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
        headers=SECURITY_HEADERS,
    )
