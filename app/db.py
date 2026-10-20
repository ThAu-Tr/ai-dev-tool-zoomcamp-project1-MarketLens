from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import database_url


class Base(DeclarativeBase):
    pass


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    engine = create_engine(database_url(), pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    with get_session_factory()() as session:
        yield session
