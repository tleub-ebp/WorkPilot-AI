"""
Database connection and session management for Build Analytics.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .database_schema import Base

# Database configuration
DATABASE_URL = os.getenv(
    "ANALYTICS_DATABASE_URL", 
    "sqlite:///./analytics.db"
)

# Create engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=os.getenv("DEBUG", "").lower() in ("1", "true", "yes")
    )
else:
    engine = create_engine(
        DATABASE_URL,
        echo=os.getenv("DEBUG", "").lower() in ("1", "true", "yes")
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """Initialize the analytics database."""
    create_tables()
    print("[Analytics] Database initialized successfully")
