"""Testes de serviços."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.main import app
from app.db.base import Base
from app.db.config import get_database_url
from app.db.session import configure_engine, get_db


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "services.db"
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


def _auth_headers(client: TestClient, email: str = "services@laje.com") -> dict[str, str]:
    sign_up = client.post(
        "/api/auth/sign-up",
        json={
            "email": email,
            "password": "senha-forte",
            "firstName": "Chef",
            "lastName": "Servico",
        },
    )
    assert sign_up.status_code == 201, sign_up.text
    return {"Authorization": f"Bearer {sign_up.json()['accessToken']}"}


def _create_recipe(client: TestClient, headers: dict[str, str], title: str = "Prato") -> str:
    response = client.post(
        "/v1/recipes",
        headers=headers,
        json={
            "title": title,
            "block_ids": ["camarao_branco"],
            "steps": [],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_service_crud(client: TestClient):
    headers = _auth_headers(client)
    recipe_id = _create_recipe(client, headers)

    create = client.post(
        "/v1/services",
        headers=headers,
        json={
            "name": "Almoço degustação",
            "service_date": "2026-08-15",
            "recipe_ids": [recipe_id],
            "notes": "12 capas",
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    service_id = body["id"]
    assert body["name"] == "Almoço degustação"
    assert body["service_date"] == "2026-08-15"
    assert body["recipe_ids"] == [recipe_id]

    listed = client.get("/v1/services", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    updated = client.put(
        f"/v1/services/{service_id}",
        headers=headers,
        json={"name": "Jantar", "service_date": "2026-08-16"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Jantar"
    assert updated.json()["service_date"] == "2026-08-16"

    deleted = client.delete(f"/v1/services/{service_id}", headers=headers)
    assert deleted.status_code == 204


def test_service_rejects_foreign_recipe(client: TestClient):
    headers_a = _auth_headers(client, "svc-a@laje.com")
    headers_b = _auth_headers(client, "svc-b@laje.com")
    recipe_a = _create_recipe(client, headers_a)

    bad = client.post(
        "/v1/services",
        headers=headers_b,
        json={
            "name": "Roubo",
            "service_date": str(date.today()),
            "recipe_ids": [recipe_a],
        },
    )
    assert bad.status_code == 400
