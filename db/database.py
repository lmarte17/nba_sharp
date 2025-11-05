import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


Base = declarative_base()


def get_engine(database_url: Optional[str] = None):
    """
    Create a SQLAlchemy Engine for the provided Postgres URL.

    Supports Neon by passing an sslmode in the URL, e.g.:
    postgresql+psycopg://user:pass@host/db?sslmode=require
    """
    db_url = database_url or os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Provide via env or pass to get_engine()."
        )
    return create_engine(db_url, pool_pre_ping=True, future=True)


def get_session_maker(engine):
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


