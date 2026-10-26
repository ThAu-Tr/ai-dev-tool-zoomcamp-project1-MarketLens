from __future__ import annotations

from sqlalchemy.exc import OperationalError
from sqlalchemy import create_engine
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.db import Base, get_session
from app.main import create_app
from app import models  # noqa: F401 - register metadata for the SQLite fixture


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_readiness_returns_empty_200_when_database_query_succeeds(session_factory) -> None:
    app = create_app()

    def local_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = local_session
    response = TestClient(app).get("/health/ready")

    assert response.status_code == 200
    assert response.content == b""


def test_readiness_returns_empty_503_without_database_details_on_database_error() -> None:
    app = create_app()

    def failing_session():
        class UnavailableSession:
            def execute(self, _statement):
                raise OperationalError("SELECT 1", {}, RuntimeError("database URL must not leak"))

            def rollback(self):
                return None

        yield UnavailableSession()

    app.dependency_overrides[get_session] = failing_session
    response = TestClient(app).get("/health/ready")

    assert response.status_code == 503
    assert response.content == b""
    assert b"database URL must not leak" not in response.content
