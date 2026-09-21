"""Public chat queue consumed by an outbound-only, independently authenticated worker."""
import hashlib
import os
import secrets
import time
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as postgres_insert

from app.database import get_db
from app.models import SupportJob, SupportState, Tool, News
from app.security import bearer

router = APIRouter(tags=["在线客服"])
templates = Jinja2Templates(directory="templates")
FALLBACK = "暂时未能获取客服回复。您可以稍后重试，或邮件联系 304633698@qq.com。"


def now():
    return int(time.time())


def require_worker(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    key = os.getenv("SITE_SUPPORT_WORKER_TOKEN", "")
    if len(key) < 32:
        raise HTTPException(503, "Support worker is not configured")
    if key in {os.getenv("SITE_ADMIN_TOKEN", ""), os.getenv("SITE_ANALYTICS_TOKEN", "")}:
        raise HTTPException(503, "Use a separate support worker token")
    candidate = credentials.credentials if credentials else ""
    if not secrets.compare_digest(candidate.encode(), key.encode()):
        raise HTTPException(401, "Invalid support worker token")


def session_owner(x_support_session: str = Header(..., pattern=r"^[a-f0-9]{64}$")):
    return hashlib.sha256(x_support_session.encode()).hexdigest()


def insert_for(db):
    return postgres_insert if db.bind.dialect.name == "postgresql" else sqlite_insert


def online(db):
    state = db.get(SupportState, "worker")
    return bool(state and state.expires > now())


def cleanup(db):
    db.query(SupportJob).filter(SupportJob.created < now() - 7 * 86400).delete()
    db.query(SupportState).filter(SupportState.expires < now()).delete()


def limit(db, key, maximum, window):
    bucket = now() // window
    record_key = f"{key}:{bucket}"
    stmt = insert_for(db)(SupportState).values(key=record_key, value=1, expires=(bucket + 1) * window)
    stmt = stmt.on_conflict_do_update(index_elements=[SupportState.key],
        set_={"value": SupportState.value + 1}, where=SupportState.value < maximum)
    if db.execute(stmt).rowcount != 1:
        db.rollback()
        raise HTTPException(429, "咨询次数较多，请稍后重试，或通过邮箱联系。", headers={"Retry-After": str(window - now() % window)})


class Message(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=3000)


class Question(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    request_id: UUID
    message: str = Field(min_length=1, max_length=1000)
    history: list[Message] = Field(default_factory=list, max_length=8)


class Answer(BaseModel):
    lease: str = Field(min_length=32, max_length=64)
    answer: str = Field(default="", max_length=6000)
    success: bool = True


@router.get("/contact", response_class=HTMLResponse, include_in_schema=False)
def contact_page(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})


@router.get("/api/support/status")
def support_status(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return {"online": online(db), "email": "304633698@qq.com"}


@router.post("/api/support/chat", status_code=202)
def ask(payload: Question, request: Request, response: Response, owner: str = Depends(session_owner), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    existing = db.get(SupportJob, str(payload.request_id))
    if existing:
        if existing.owner != owner:
            raise HTTPException(409, "Request ID already used")
        return {"id": existing.id}
    if not online(db):
        raise HTTPException(503, FALLBACK)
    cleanup(db)
    ip = request.client.host if request.client else "unknown"
    identity = hashlib.sha256(ip.encode()).hexdigest()
    limit(db, "minute:" + identity, 6, 60)
    limit(db, "day:" + identity, 30, 86400)
    limit(db, "global", int(os.getenv("SUPPORT_DAILY_LIMIT", "200")), 86400)
    if db.query(SupportJob).filter(SupportJob.owner == owner, SupportJob.status.in_(["pending", "working"]), SupportJob.expires > now()).first():
        db.rollback()
        raise HTTPException(409, "上一条咨询仍在处理中，请稍候。")
    job = SupportJob(id=str(payload.request_id), owner=owner,
        messages=[m.model_dump() for m in payload.history] + [{"role": "user", "content": payload.message}],
        status="pending", created=now(), expires=now() + 150)
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.get(SupportJob, str(payload.request_id))
        if not existing or existing.owner != owner:
            raise HTTPException(409, "Request ID already used")
    return {"id": str(payload.request_id)}


@router.get("/api/support/chat/{job_id}")
def reply(job_id: UUID, response: Response, owner: str = Depends(session_owner), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    job = db.get(SupportJob, str(job_id))
    if not job or job.owner != owner:
        raise HTTPException(404, "Conversation not found")
    if job.expires <= now() and job.status in {"pending", "working"}:
        return {"status": "failed", "answer": FALLBACK}
    return {"status": job.status, "answer": job.answer if job.status == "done" else FALLBACK if job.status == "failed" else None}


def public_context(db):
    lines = ["公司：深圳市奇点临近计算机技术研发有限责任公司。所在地：深圳。邮箱：304633698@qq.com。",
        "服务：MCP 工具开发、应用与 API 集成、AI 应用方案咨询。合作流程：描述问题、明确范围、分步交付。",
        "页面：/services 服务介绍；/tools 工具目录；/guide 使用指南；/news 新闻；/about 关于我们。",
        "没有公开报价、联系电话、具体办公地址或响应时间承诺。定价、工期和商务合作需邮件沟通。工具目录不代表每个端点已实现。"]
    for tool in db.query(Tool).filter(Tool.is_active == True).order_by(Tool.id).limit(30):
        lines.append(f"工具：{tool.name}；{(tool.short_description or tool.description or '')[:240]}；路径：/tools/{tool.slug}")
    for article in db.query(News).filter(News.status == "published").order_by(News.published_at.desc()).limit(3):
        lines.append(f"已发布新闻：{article.title}；{article.summary}；路径：/news/{article.slug}")
    return "\n".join(lines)[:10000]


@router.post("/api/support/worker/claim", dependencies=[Depends(require_worker)])
def claim(db: Session = Depends(get_db)):
    cleanup(db)
    stmt = insert_for(db)(SupportState).values(key="worker", value=now(), expires=now() + 45)
    db.execute(stmt.on_conflict_do_update(index_elements=[SupportState.key], set_={"value": now(), "expires": now() + 45}))
    db.commit()
    job = db.query(SupportJob).filter(SupportJob.status == "pending", SupportJob.expires > now()).order_by(SupportJob.created).first()
    if not job:
        return {"job": None}
    lease = secrets.token_hex(32)
    changed = db.execute(update(SupportJob).where(SupportJob.id == job.id, SupportJob.status == "pending").values(status="working", lease=lease))
    db.commit()
    if changed.rowcount != 1:
        return {"job": None}
    return {"job": {"id": job.id, "lease": lease, "messages": job.messages, "context": public_context(db)}}


@router.post("/api/support/worker/heartbeat", dependencies=[Depends(require_worker)])
def heartbeat(db: Session = Depends(get_db)):
    state = db.get(SupportState, "worker")
    if state:
        state.expires = now() + 45
        db.commit()
    return {"ok": True}


@router.post("/api/support/worker/{job_id}/complete", dependencies=[Depends(require_worker)])
def complete(job_id: UUID, payload: Answer, db: Session = Depends(get_db)):
    if payload.success and not payload.answer.strip():
        raise HTTPException(422, "Answer cannot be empty")
    job = db.get(SupportJob, str(job_id))
    if not job or not secrets.compare_digest(job.lease or "", payload.lease):
        raise HTTPException(409, "Job lease mismatch")
    if job.status in {"done", "failed"}:
        return {"ok": True}
    changed = db.execute(update(SupportJob).where(SupportJob.id == job.id, SupportJob.status == "working", SupportJob.expires > now()).values(
        status="done" if payload.success else "failed", answer=payload.answer.strip() if payload.success else FALLBACK))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Job expired")
    db.commit()
    return {"ok": True}
