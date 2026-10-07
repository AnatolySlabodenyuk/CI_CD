import os

import psycopg2
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

from src.app import app, redis_client

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root_uses_postgres_and_redis():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Приложение работает!"
    assert data["postgres_version"].startswith("PostgreSQL 15.")
    assert isinstance(data["visit_count"], str)
    assert int(data["visit_count"]) >= 1
    assert int(redis_client.get("visit_count")) >= int(data["visit_count"])


def test_counter_increases():
    first = int(client.get("/").json()["visit_count"])
    second = int(client.get("/").json()["visit_count"])
    assert second > first


def test_migration_schema():
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        schema = inspect(engine)
        columns = {column["name"]: column for column in schema.get_columns("users")}
        assert set(columns) == {"id", "name", "email", "created_at"}
        assert columns["name"]["nullable"] is False
        assert columns["email"]["nullable"] is False
        assert columns["name"]["type"].length == 50
        assert columns["email"]["type"].length == 100
        with engine.connect() as connection:
            from sqlalchemy import text
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "001_initial"
    finally:
        engine.dispose()


def test_connection_closed_when_query_fails(monkeypatch):
    class BrokenCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, query):
            raise psycopg2.OperationalError("simulated query error")

    class Connection:
        closed = False

        def cursor(self):
            return BrokenCursor()

        def close(self):
            self.closed = True

    connection = Connection()
    monkeypatch.setattr(psycopg2, "connect", lambda *args, **kwargs: connection)
    with TestClient(app, raise_server_exceptions=False) as failing_client:
        assert failing_client.get("/").status_code == 500
    assert connection.closed
