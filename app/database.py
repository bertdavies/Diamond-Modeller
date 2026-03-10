"""
Diamond Modeler — database engine and session management.

Author: Albert Davies
License: CC BY-NC-SA 4.0
"""

from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import os

# Database URL - using SQLite for local development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./diamond_modeler.db")

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    """Create database tables"""
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    with Session(engine) as session:
        yield session

