from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ToolBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=255)
    icon_url: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []
    is_active: bool = True
    api_endpoint: Optional[str] = None


class ToolCreate(ToolBase):
    pass


class ToolUpdate(ToolBase):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = Field(
        None, min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$"
    )


class ToolResponse(ToolBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ToolListResponse(BaseModel):
    total: int
    items: List[ToolResponse]


class ApiLogCreate(BaseModel):
    endpoint: str
    method: str
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None


class ToolUsageStats(BaseModel):
    tool_slug: str
    tool_name: str
    total_calls: int
    calls_last_24h: int
    avg_response_time_ms: float


class ApiStatsResponse(BaseModel):
    total_tools: int
    total_api_calls: int
    calls_last_24h: int
    popular_tools: List[dict]
