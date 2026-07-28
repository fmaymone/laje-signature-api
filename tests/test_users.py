"""Testes da entidade User + DB."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.config import get_database_url
from app.db.session import configure_engine, get_db
from api.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("SKIP_DB_MIGRATE", "1")
    get_database_url.cache_clear()
    engine = configure_engine(url)
    Base.metadata.create_all(bind=engine)

    def _override_db():
        db: Session = __import__("app.db.session", fromlist=["SessionLocal"]).SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_create_and_get_user(client: TestClient):
    response = client.post(
        "/v1/users",
        json={
            "email": "fernando@laje.com",
            "full_name": "Fernando Laje",
            "password": "senha-forte",
            "role": "chef",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "fernando@laje.com"
    assert body["role"] == "chef"
    assert "hashed_password" not in body

    user_id = body["id"]
    got = client.get(f"/v1/users/{user_id}")
    assert got.status_code == 200
    assert got.json()["full_name"] == "Fernando Laje"


def test_duplicate_email(client: TestClient):
    payload = {
        "email": "dup@laje.com",
        "full_name": "Dup",
        "password": "senha-forte",
    }
    assert client.post("/v1/users", json=payload).status_code == 201
    assert client.post("/v1/users", json=payload).status_code == 409


def test_list_users(client: TestClient):
    client.post(
        "/v1/users",
        json={"email": "a@laje.com", "full_name": "A", "password": "senha-forte"},
    )
    response = client.get("/v1/users")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert len(body["items"]) >= 1


def test_get_missing_user(client: TestClient):
    response = client.get(f"/v1/users/{uuid.uuid4()}")
    assert response.status_code == 404


def test_health_includes_database(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "ok"
