"""Testes de receitas persistidas."""

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
    db_file = tmp_path / "recipes.db"
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


def _auth_headers(client: TestClient, email: str = "recipes@laje.com") -> dict[str, str]:
    sign_up = client.post(
        "/api/auth/sign-up",
        json={
            "email": email,
            "password": "senha-forte",
            "firstName": "Chef",
            "lastName": "Receitas",
        },
    )
    assert sign_up.status_code == 201, sign_up.text
    return {"Authorization": f"Bearer {sign_up.json()['accessToken']}"}


def test_recipe_crud_with_blocks_and_steps(client: TestClient):
    headers = _auth_headers(client)

    create = client.post(
        "/v1/recipes",
        headers=headers,
        json={
            "title": "Camarão na brasa",
            "notes": "serviço de almoço",
            "block_ids": ["camarao_branco", "coentro"],
            "steps": [
                {
                    "id": "s1",
                    "process": "brasa",
                    "description": "Grelhar o camarão",
                    "time_before_service_minutes": 20,
                    "duration_minutes": 15,
                },
                {
                    "id": "s2",
                    "process": "montar",
                    "description": "Finalizar com coentro",
                    "time_before_service_minutes": 0,
                },
            ],
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    recipe_id = body["id"]
    assert body["title"] == "Camarão na brasa"
    assert body["block_ids"] == ["camarao_branco", "coentro"]
    assert len(body["steps"]) == 2
    assert body["steps"][0]["duration_minutes"] == 15
    assert body["steps"][1]["duration_minutes"] == 10  # default
    assert body["composition_id"] is None

    listed = client.get("/v1/recipes", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    updated = client.put(
        f"/v1/recipes/{recipe_id}",
        headers=headers,
        json={
            "steps": [
                {
                    "id": "s1",
                    "process": "brasa",
                    "description": "Grelhar",
                    "time_before_service_minutes": 30,
                }
            ]
        },
    )
    assert updated.status_code == 200, updated.text
    assert len(updated.json()["steps"]) == 1
    assert updated.json()["steps"][0]["time_before_service_minutes"] == 30

    deleted = client.delete(f"/v1/recipes/{recipe_id}", headers=headers)
    assert deleted.status_code == 204


def test_recipe_optional_composition_and_ownership(client: TestClient):
    headers_a = _auth_headers(client, "chef-a@laje.com")
    headers_b = _auth_headers(client, "chef-b@laje.com")

    graph = client.post(
        "/v1/compose/graphs",
        headers=headers_a,
        json={"title": "Mar", "nodes": [], "edges": []},
    )
    assert graph.status_code == 201, graph.text
    composition_id = graph.json()["id"]

    ok = client.post(
        "/v1/recipes",
        headers=headers_a,
        json={
            "title": "Com composição",
            "composition_id": composition_id,
            "block_ids": ["camarao_branco"],
            "steps": [],
        },
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["composition_id"] == composition_id

    foreign = client.post(
        "/v1/recipes",
        headers=headers_b,
        json={
            "title": "Roubo",
            "composition_id": composition_id,
            "block_ids": [],
            "steps": [],
        },
    )
    assert foreign.status_code == 400

    recipe_id = ok.json()["id"]
    other_get = client.get(f"/v1/recipes/{recipe_id}", headers=headers_b)
    assert other_get.status_code == 404


def test_recipe_rejects_unknown_block(client: TestClient):
    headers = _auth_headers(client)
    response = client.post(
        "/v1/recipes",
        headers=headers,
        json={
            "title": "Inválida",
            "block_ids": ["bloco_que_nao_existe_xyz"],
            "steps": [],
        },
    )
    assert response.status_code == 400
