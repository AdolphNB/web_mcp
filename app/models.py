from sqlalchemy import Column, Integer, String, Text, DateTime, Date, JSON, Boolean, func
from app.database import Base


class Tool(Base):
    """工具信息表"""

    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    short_description = Column(String(255), nullable=True)
    icon_url = Column(String(500), nullable=True)
    category = Column(String(50), nullable=True)
    tags = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    api_endpoint = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ApiLog(Base):
    """API调用记录表"""

    __tablename__ = "api_logs"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(160), nullable=False)
    summary = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    source_url = Column(String(2000), nullable=True)
    status = Column(String(20), nullable=False, default="draft", index=True)
    version = Column(Integer, nullable=False, default=1)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PageViewDaily(Base):
    """Aggregate PV only: no IP, cookie, query string, or visitor fingerprint."""
    __tablename__ = "page_views_daily"

    day = Column(Date, primary_key=True)
    path = Column(String(500), primary_key=True)
    views = Column(Integer, nullable=False, default=0)


class NewsAudit(Base):
    __tablename__ = "news_audit"

    id = Column(Integer, primary_key=True)
    slug = Column(String(100), nullable=False, index=True)
    action = Column(String(30), nullable=False)
    version = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
