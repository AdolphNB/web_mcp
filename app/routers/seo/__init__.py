from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Tool
from fastapi.responses import HTMLResponse
from datetime import datetime

router = APIRouter()

SITE_URL = "https://mcptools.xin"


@router.get("/sitemap.xml", response_class=HTMLResponse)
async def sitemap(db: Session = Depends(get_db)):
    tools = db.query(Tool).filter(Tool.is_active == True).all()

    sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

    sitemap_content += f"""
  <url>
    <loc>{SITE_URL}/</loc>
    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>"""

    sitemap_content += f"""
  <url>
    <loc>{SITE_URL}/tools</loc>
    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>"""

    sitemap_content += f"""
  <url>
    <loc>{SITE_URL}/docs</loc>
    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>"""

    for tool in tools:
        lastmod = (
            tool.updated_at.strftime("%Y-%m-%d")
            if tool.updated_at
            else datetime.now().strftime("%Y-%m-%d")
        )
        sitemap_content += f"""
  <url>
    <loc>{SITE_URL}/tools/{tool.slug}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>"""

    sitemap_content += "\n</urlset>"
    return Response(content=sitemap_content, media_type="application/xml")


@router.get("/robots.txt", response_class=HTMLResponse)
async def robots():
    robots_content = f"""User-agent: *
Allow: /

Sitemap: {SITE_URL}/sitemap.xml

Crawl-delay: 1
"""
    return Response(content=robots_content, media_type="text/plain")
