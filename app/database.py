import os
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables from .env file
load_dotenv()

# Database URL - use environment variable or default to SQLite for development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mcptools.db")


engine = create_engine(DATABASE_URL, echo=os.getenv("DEBUG", "False") == "True")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
