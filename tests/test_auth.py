"""Testes de auth JWT (contrato Minimals)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.main import app
from app.db.base import Base
from app.db.config import get_database_url
from app.db.session import configure_engine, get_db


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "auth.db"
    url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
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


def test_sign_up_sign_in_me(client: TestClient):
    sign_up = client.post(
        "/api/auth/sign-up",
        json={
            "email": "chef@laje.com",
            "password": "senha-forte",
            "firstName": "Chef",
            "lastName": "Laje",
        },
    )
    assert sign_up.status_code == 201, sign_up.text
    token = sign_up.json()["accessToken"]
    assert token

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    user = me.json()["user"]
    assert user["email"] == "chef@laje.com"
    assert user["displayName"] == "Chef Laje"
    assert user["role"] == "staff"

    sign_in = client.post(
        "/api/auth/sign-in",
        json={"email": "chef@laje.com", "password": "senha-forte"},
    )
    assert sign_in.status_code == 200
    assert sign_in.json()["accessToken"]


def test_sign_in_invalid(client: TestClient):
    response = client.post(
        "/api/auth/sign-in",
        json={"email": "nobody@laje.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
