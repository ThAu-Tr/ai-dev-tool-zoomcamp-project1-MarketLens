import pytest

from app.config import database_url


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        (
            "postgres://user:secret@host/db?sslmode=require",
            "postgresql+psycopg://user:secret@host/db?sslmode=require",
        ),
        (
            "postgresql://user:secret@host/db?sslmode=require",
            "postgresql+psycopg://user:secret@host/db?sslmode=require",
        ),
        (
            "postgresql+psycopg://user:secret@host/db?sslmode=require",
            "postgresql+psycopg://user:secret@host/db?sslmode=require",
        ),
    ],
)
def test_database_url_uses_installed_postgres_driver(monkeypatch, configured, expected):
    monkeypatch.setenv("DATABASE_URL", configured)

    assert database_url() == expected


def test_database_url_requires_configuration(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL must be set"):
        database_url()
