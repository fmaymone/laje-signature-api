"""CRUD do grafo de composição (por usuário autenticado)."""

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
    db_file = tmp_path / "compose_graphs.db"
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


def _auth_headers(client: TestClient, email: str = "chef@laje.com") -> dict[str, str]:
    sign_up = client.post(
        "/api/auth/sign-up",
        json={
            "email": email,
            "password": "senha-forte",
            "firstName": "Chef",
            "lastName": "Laje",
        },
    )
    assert sign_up.status_code == 201, sign_up.text
    token = sign_up.json()["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_composition_graph_requires_auth(client: TestClient):
    response = client.get("/v1/compose/graphs")
    assert response.status_code == 401


def test_composition_graph_crud_scoped_to_user(client: TestClient):
    headers_a = _auth_headers(client, "a@laje.com")
    headers_b = _auth_headers(client, "b@laje.com")

    create = client.post(
        "/v1/compose/graphs",
        headers=headers_a,
        json={
            "title": "Sirigado + milho",
            "nodes": [
                {
                    "id": "n1",
                    "block_id": "sirigado_citrus_defumado",
                    "position": {"x": 40, "y": 80},
                },
                {
                    "id": "n2",
                    "block_id": "milho_manteiga",
                    "position": {"x": 320, "y": 80},
                },
            ],
            "edges": [
                {
                    "id": "e1",
                    "source": "n1",
                    "target": "n2",
                    "sourceHandle": "right",
                    "targetHandle": "left",
                }
            ],
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    graph_id = body["id"]
    assert body["title"] == "Sirigado + milho"
    assert body["owner_id"]
    assert len(body["nodes"]) == 2

    listed_a = client.get("/v1/compose/graphs", headers=headers_a)
    assert listed_a.status_code == 200
    assert listed_a.json()["total"] == 1

    listed_b = client.get("/v1/compose/graphs", headers=headers_b)
    assert listed_b.status_code == 200
    assert listed_b.json()["total"] == 0

    forbidden = client.get(f"/v1/compose/graphs/{graph_id}", headers=headers_b)
    assert forbidden.status_code == 404

    fetched = client.get(f"/v1/compose/graphs/{graph_id}", headers=headers_a)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == graph_id

    updated = client.put(
        f"/v1/compose/graphs/{graph_id}",
        headers=headers_a,
        json={
            "title": "Sirigado revisado",
            "nodes": [
                {
                    "id": "n1",
                    "block_id": "sirigado_citrus_defumado",
                    "position": {"x": 100, "y": 120},
                }
            ],
            "edges": [],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Sirigado revisado"
    assert len(updated.json()["nodes"]) == 1
    assert updated.json()["edges"] == []

    deleted = client.delete(f"/v1/compose/graphs/{graph_id}", headers=headers_a)
    assert deleted.status_code == 204

    missing = client.get(f"/v1/compose/graphs/{graph_id}", headers=headers_a)
    assert missing.status_code == 404
