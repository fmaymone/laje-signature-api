"""CRUD do grafo de composição."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.config import get_database_url
from app.db.session import configure_engine, get_db
from api.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "compose_graphs.db"
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


def test_composition_graph_crud(client: TestClient):
    create = client.post(
        "/v1/compose/graphs",
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
    assert len(body["nodes"]) == 2
    assert body["edges"][0]["sourceHandle"] == "right"

    listed = client.get("/v1/compose/graphs")
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    fetched = client.get(f"/v1/compose/graphs/{graph_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == graph_id

    updated = client.put(
        f"/v1/compose/graphs/{graph_id}",
        json={
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
    assert len(updated.json()["nodes"]) == 1
    assert updated.json()["edges"] == []

    deleted = client.delete(f"/v1/compose/graphs/{graph_id}")
    assert deleted.status_code == 204

    missing = client.get(f"/v1/compose/graphs/{graph_id}")
    assert missing.status_code == 404
