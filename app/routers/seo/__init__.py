from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Tool, News

router = APIRouter()
SITE_URL = "https://singularitynear.com"


@router.get("/sitemap.xml")
def sitemap(db: Session = Depends(get_db)):
    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    def add(path, modified=None):
        node = SubElement(root, "url")
        SubElement(node, "loc").text = SITE_URL + path
        if modified:
            SubElement(node, "lastmod").text = modified.strftime("%Y-%m-%d")

    for path in ("/", "/tools", "/services", "/about", "/guide", "/news"):
        add(path)
    for tool in db.query(Tool).filter(Tool.is_active == True).all():
        add("/tools/" + tool.slug, tool.updated_at or tool.created_at)
    for article in db.query(News).filter(News.status == "published").all():
        add("/news/" + article.slug, article.updated_at or article.published_at)
    return Response(tostring(root, encoding="utf-8", xml_declaration=True), media_type="application/xml")


@router.get("/robots.txt")
def robots():
    return Response(f"User-agent: *\nAllow: /\nDisallow: /api/admin/\n\nSitemap: {SITE_URL}/sitemap.xml\n", media_type="text/plain")
