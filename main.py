from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routers import tools
from app.routers import seo
from app.middleware import log_api_call

app = FastAPI(
    title="mcptools.xin API",
    description="基础 FastAPI 应用，包含 CORS 和简单错误处理",
    version="0.1.0",
)

# CORS for development: allow all origins
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/res", StaticFiles(directory="res"), name="res")

# Add API logging middleware
app.middleware("http")(log_api_call)
# Include routers
app.include_router(tools.router, prefix="/api")
app.include_router(seo.router)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """公司首页"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/tools", response_class=HTMLResponse)
async def tools_list(request: Request):
    """工具列表页面"""
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.models import Tool

    db: Session = SessionLocal()
    try:
        tools = db.query(Tool).filter(Tool.is_active == True).all()
        return templates.TemplateResponse(
            "tools/index.html", {"request": request, "tools": tools}
        )
    finally:
        db.close()


@app.get("/tools/{slug}", response_class=HTMLResponse)
async def tools_detail(slug: str, request: Request):
    """工具详情页面"""
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.models import Tool

    db: Session = SessionLocal()
    try:
        tool = db.query(Tool).filter(Tool.slug == slug, Tool.is_active == True).first()
        if tool is None:
            return templates.TemplateResponse(
                "404.html", {"request": request}, status_code=404
            )
        return templates.TemplateResponse(
            "tools/detail.html", {"request": request, "tool": tool}
        )
    finally:
        db.close()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Basic error handler, do not leak internal details in production
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )
