#!/usr/bin/env python3
"""
Seed database with sample tool data.
"""

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Tool, Base
from datetime import datetime


def seed_data():
    """Insert sample tool data into the database."""
    print("Seeding sample tool data...")

    db: Session = SessionLocal()
    try:
        # Check if data already exists
        existing_count = db.query(Tool).count()
        if existing_count > 0:
            print(f"⚠ Database already has {existing_count} tools. Skipping seed.")
            return

        # Sample tools
        tools_data = [
            {
                "name": "文本转换工具",
                "slug": "text-converter",
                "description": "支持多种文本格式转换的工具，包括大写转换、小写转换、大小写反转、驼峰命名转换等功能。",
                "short_description": "多功能文本格式转换工具，支持大小写、驼峰命名等转换。",
                "icon_url": "https://api.dicebear.com/7.x/icons/svg?seed=text",
                "category": "文本处理",
                "tags": ["文本", "转换", "工具"],
                "is_active": True,
                "api_endpoint": "/api/v1/text-convert",
            },
            {
                "name": "JSON 格式化器",
                "slug": "json-formatter",
                "description": "在线 JSON 格式化和验证工具，支持压缩、美化、语法检查等功能。提供语法高亮和错误提示。",
                "short_description": "专业的 JSON 格式化、压缩和验证工具。",
                "icon_url": "https://api.dicebear.com/7.x/icons/svg?seed=json",
                "category": "数据格式",
                "tags": ["JSON", "格式化", "验证"],
                "is_active": True,
                "api_endpoint": "/api/v1/json-format",
            },
            {
                "name": "Base64 编解码器",
                "slug": "base64-encoder",
                "description": "快捷的 Base64 编码和解码工具，支持文本和文件的编码解码操作。界面简洁，使用方便。",
                "short_description": "支持文本和文件的 Base64 编码解码。",
                "icon_url": "https://api.dicebear.com/7.x/icons/svg?seed=base64",
                "category": "编码解码",
                "tags": ["Base64", "编码", "解码"],
                "is_active": True,
                "api_endpoint": "/api/v1/base64",
            },
            {
                "name": "URL 编码解码",
                "slug": "url-encoder",
                "description": "URL 编码和解码工具，支持百分号编码，处理特殊字符和中文，让 URL 更加规范和安全。",
                "short_description": "URL 编码和百分号编码解码工具。",
                "icon_url": "https://api.dicebear.com/7.x/icons/svg?seed=url",
                "category": "编码解码",
                "tags": ["URL", "编码", "百分号编码"],
                "is_active": True,
                "api_endpoint": "/api/v1/url-encode",
            },
            {
                "name": "正则表达式测试器",
                "slug": "regex-tester",
                "description": "强大的正则表达式测试和调试工具，支持多行匹配、捕获组、替换预览等功能，带有常用正则库。",
                "short_description": "正则表达式测试和调试工具。",
                "icon_url": "https://api.dicebear.com/7.x/icons/svg?seed=regex",
                "category": "开发工具",
                "tags": ["正则", "Regex", "调试"],
                "is_active": True,
                "api_endpoint": "/api/v1/regex-test",
            },
            {
                "name": "时间戳转换",
                "slug": "timestamp-converter",
                "description": "时间戳与日期时间互转工具，支持 Unix 时间戳、毫秒时间戳，支持多种时间格式和时区。",
                "short_description": "时间戳与日期时间相互转换工具。",
                "icon_url": "https://api.dicebear.com/7.x/icons/svg?seed=time",
                "category": "时间日期",
                "tags": ["时间戳", "日期", "转换"],
                "is_active": True,
                "api_endpoint": "/api/v1/timestamp-convert",
            },
            {
                "name": "颜色转换工具",
                "slug": "color-converter",
                "description": "颜色格式转换工具，支持 HEX、RGB、HSL、CMYK 等多种颜色格式的相互转换，提供色板预览。",
                "short_description": "HEX、RGB、HSL、CMYK 等颜色格式转换工具。",
                "icon_url": "https://api.dicebear.com/7.x/icons/svg?seed=color",
                "category": "颜色工具",
                "tags": ["颜色", "HEX", "RGB", "HSL"],
                "is_active": True,
                "api_endpoint": "/api/v1/color-convert",
            },
            {
                "name": "哈希生成器",
                "slug": "hash-generator",
                "description": "多种哈希算法生成工具，支持 MD5、SHA-1、SHA-256、SHA-512 等常用哈希算法的加密生成。",
                "short_description": "MD5、SHA-1、SHA-256 等哈希算法生成工具。",
                "icon_url": "https://api.dicebear.com/7.x/icons/svg?seed=hash",
                "category": "加密安全",
                "tags": ["哈希", "MD5", "SHA", "加密"],
                "is_active": True,
                "api_endpoint": "/api/v1/hash-generate",
            },
            {
                "name": "UUID 生成器",
                "slug": "uuid-generator",
                "description": "UUID/GUID 生成工具，支持 UUID v1、v3、v4、v5 等多种版本，支持批量生成和使用场景定制。",
                "short_description": "支持 UUID v1-v4 多种版本的生成器。",
                "icon_url": "https://api.dicebear.com/7.x/icons/svg?seed=uuid",
                "category": "生成工具",
                "tags": ["UUID", "GUID", "ID生成"],
                "is_active": True,
                "api_endpoint": "/api/v1/uuid-generate",
            },
        ]

        # Insert tools
        for tool_data in tools_data:
            tool = Tool(**tool_data)
            db.add(tool)

        db.commit()
        print(f"✓ Successfully inserted {len(tools_data)} sample tools")

    except Exception as e:
        print(f"✗ Error seeding data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
    print("Data seeding complete! ✓")
