#!/usr/bin/env python3
"""
Database migration script for mcptools.xin
Creates all database tables using SQLAlchemy
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.chdir(project_root)

from app.database import engine, Base, SessionLocal
from app.models import Tool, ApiLog


def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")


def drop_tables():
    """Drop all database tables (use with caution)"""
    print("Dropping database tables...")
    Base.metadata.drop_all(bind=engine)
    print("✓ Database tables dropped")


def seed_sample_data():
    """Insert sample data for testing"""
    print("Seeding sample data...")
    db = SessionLocal()

    try:
        sample_tools = [
            Tool(
                name="JSON Formatter",
                slug="json-formatter",
                description="Beautifully format JSON data for better readability",
                short_description="Format and validate JSON data",
                category="Developer Tools",
                tags=["json", "formatter", "developer"],
                icon_url=None,
                api_endpoint="/api/format/json",
                is_active=True,
            ),
            Tool(
                name="Base64 Encoder/Decoder",
                slug="base64-encoder-decoder",
                description="Encode and decode Base64 strings easily",
                short_description="Base64 encode/decode tool",
                category="Converter",
                tags=["base64", "encoder", "decoder", "converter"],
                icon_url=None,
                api_endpoint="/api/convert/base64",
                is_active=True,
            ),
            Tool(
                name="URL Encoder/Decoder",
                slug="url-encoder-decoder",
                description="Encode and decode URLs with special characters",
                short_description="URL encode/decode utility",
                category="Converter",
                tags=["url", "encoder", "decoder", "converter"],
                icon_url=None,
                api_endpoint="/api/convert/url",
                is_active=True,
            ),
            Tool(
                name="Color Converter",
                slug="color-converter",
                description="Convert colors between HEX, RGB, HSL formats",
                short_description="Color palette converter",
                category="Design",
                tags=["color", "converter", "design", "hex", "rgb", "hsl"],
                icon_url=None,
                api_endpoint="/api/convert/color",
                is_active=True,
            ),
            Tool(
                name="Markdown Preview",
                slug="markdown-preview",
                description="Preview Markdown formatted text in real-time",
                short_description="Live Markdown renderer",
                category="Editor",
                tags=["markdown", "preview", "editor", "writing"],
                icon_url=None,
                api_endpoint="/api/render/markdown",
                is_active=True,
            ),
        ]

        for tool in sample_tools:
            db.add(tool)

        db.commit()
        print(f"✓ Added {len(sample_tools)} sample tools")

        # Verify insertion
        count = db.query(Tool).count()
        print(f"✓ Total tools in database: {count}")

    except Exception as e:
        print(f"✗ Error seeding data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def show_stats():
    """Show database statistics"""
    print("Database statistics:")
    db = SessionLocal()

    try:
        tool_count = db.query(Tool).count()
        active_tools = db.query(Tool).filter(Tool.is_active == True).count()
        api_log_count = db.query(ApiLog).count()

        print(f"  Total tools: {tool_count}")
        print(f"  Active tools: {active_tools}")
        print(f"  API logs: {api_log_count}")

    finally:
        db.close()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Database migration tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # migrate command
    subparsers.add_parser("migrate", help="Create database tables")

    # drop command
    subparsers.add_parser("drop", help="Drop all database tables")

    # seed command
    subparsers.add_parser("seed", help="Seed sample data")

    # stats command
    subparsers.add_parser("stats", help="Show database statistics")

    # reset command (drop + migrate + seed)
    subparsers.add_parser("reset", help="Drop, migrate and seed database")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "migrate":
        create_tables()
    elif args.command == "drop":
        drop_tables()
    elif args.command == "seed":
        seed_sample_data()
    elif args.command == "stats":
        show_stats()
    elif args.command == "reset":
        drop_tables()
        create_tables()
        seed_sample_data()


if __name__ == "__main__":
    main()
