#!/usr/bin/env python3
"""
Database initialization script.
Creates all tables defined in the models.
"""

import os
from sqlalchemy import create_engine, text
from app.database import Base, DATABASE_URL, engine
from app.models import Tool, ApiLog


def init_db():
    """Initialize database by creating all tables."""
    print(
        f"Connecting to database: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}"
    )

    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✓ All tables created successfully")
        # Verify tables exist (SQLite or PostgreSQL)
        if 'sqlite' in DATABASE_URL:
            # SQLite specific
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
                tables = [row[0] for row in result]
        else:
            # PostgreSQL specific
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                )
                tables = [row[0] for row in result]
        print(f"✓ Tables in database: {', '.join(tables)}")

    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        raise


if __name__ == "__main__":
    init_db()
    print("\nDatabase initialization complete! ✓")
