from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.database import get_db
from app.models import Tool, ApiLog
from app.schemas import ToolResponse, ToolListResponse, ApiStatsResponse, ToolUsageStats

router = APIRouter()


@router.get("/tools", response_model=ToolListResponse)
def read_tools(
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of results to return"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
):
    tools = db.query(Tool).filter(Tool.is_active == True)

    if category:
        tools = tools.filter(Tool.category == category)

    total = tools.count()
    items = tools.offset(skip).limit(limit).all()

    return {"total": total, "items": items}


@router.get("/tools/{slug}", response_model=ToolResponse)
def read_tool(slug: str, db: Session = Depends(get_db)):
    tool = db.query(Tool).filter(Tool.slug == slug, Tool.is_active == True).first()
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


@router.get("/tools/{slug}/usage", response_model=ToolUsageStats)
def get_tool_usage(slug: str, db: Session = Depends(get_db)):
    tool = db.query(Tool).filter(Tool.slug == slug, Tool.is_active == True).first()
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")

    total_calls = (
        db.query(func.count(ApiLog.id))
        .filter(ApiLog.endpoint.like(f"%/tools/{slug}%"))
        .scalar()
    )

    last_24h_calls = (
        db.query(func.count(ApiLog.id))
        .filter(
            ApiLog.endpoint.like(f"%/tools/{slug}%"),
            ApiLog.created_at >= func.now() - func.interval("24 hours"),
        )
        .scalar()
    )

    avg_response_time = (
        db.query(func.avg(ApiLog.response_time_ms))
        .filter(ApiLog.endpoint.like(f"%/tools/{slug}%"))
        .scalar()
    )

    return {
        "tool_slug": slug,
        "tool_name": tool.name,
        "total_calls": total_calls or 0,
        "calls_last_24h": last_24h_calls or 0,
        "avg_response_time_ms": round(avg_response_time, 2) if avg_response_time else 0,
    }


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    categories = (
        db.query(Tool.category)
        .filter(Tool.is_active == True, Tool.category.isnot(None))
        .distinct()
        .all()
    )

    return {"categories": [cat[0] for cat in categories if cat[0]]}


@router.get("/stats", response_model=ApiStatsResponse)
def get_api_stats(db: Session = Depends(get_db)):
    total_tools = db.query(func.count(Tool.id)).filter(Tool.is_active == True).scalar()

    total_api_calls = db.query(func.count(ApiLog.id)).scalar()

    last_24h_calls = (
        db.query(func.count(ApiLog.id))
        .filter(ApiLog.created_at >= func.now() - func.interval("24 hours"))
        .scalar()
    )

    popular_tools = (
        db.query(Tool.name, Tool.slug, func.count(ApiLog.id).label("call_count"))
        .join(ApiLog, ApiLog.endpoint.like(f"%/tools/%" + Tool.slug + "%"))
        .filter(Tool.is_active == True)
        .group_by(Tool.name, Tool.slug)
        .order_by(func.count(ApiLog.id).desc())
        .limit(5)
        .all()
    )

    return {
        "total_tools": total_tools or 0,
        "total_api_calls": total_api_calls or 0,
        "calls_last_24h": last_24h_calls or 0,
        "popular_tools": [
            {"name": t[0], "slug": t[1], "call_count": t[2]} for t in popular_tools
        ],
    }
