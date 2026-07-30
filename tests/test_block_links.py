"""Testes de ligações ponderadas entre blocos."""

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
    db_file = tmp_path / "block_links.db"
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


def _auth_headers(client: TestClient) -> dict[str, str]:
    sign_up = client.post(
        "/api/auth/sign-up",
        json={
            "email": "links@laje.com",
            "password": "senha-forte",
            "firstName": "Chef",
            "lastName": "Links",
        },
    )
    assert sign_up.status_code == 201, sign_up.text
    return {"Authorization": f"Bearer {sign_up.json()['accessToken']}"}


def test_block_link_crud_and_weight(client: TestClient):
    headers = _auth_headers(client)

    create = client.post(
        "/v1/block-links",
        headers=headers,
        json={
            "source_block_id": "carne_de_sol",
            "target_block_id": "jerimum",
            "weight": 3,
            "notes": "clássico sertão",
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    link_id = body["id"]
    assert body["weight"] == 3

    listed = client.get("/v1/block-links", params={"block_id": "carne_de_sol"})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    updated = client.put(
        f"/v1/block-links/{link_id}",
        headers=headers,
        json={"weight": 1},
    )
    assert updated.status_code == 200
    assert updated.json()["weight"] == 1

    bad = client.post(
        "/v1/block-links",
        headers=headers,
        json={
            "source_block_id": "carne_de_sol",
            "target_block_id": "carne_de_sol",
            "weight": 2,
        },
    )
    assert bad.status_code == 422

    deleted = client.delete(f"/v1/block-links/{link_id}", headers=headers)
    assert deleted.status_code == 204


def test_block_links_bulk_upsert(client: TestClient):
    headers = _auth_headers(client)

    first = client.post(
        "/v1/block-links/bulk",
        headers=headers,
        json={
            "source_block_id": "camarao_branco",
            "links": [
                {"target_block_id": "coentro", "weight": 3},
                {"target_block_id": "limao_galego", "weight": 2},
                {"target_block_id": "bloco_inexistente_xyz", "weight": 2},
            ],
        },
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["created"] == 2
    assert body["skipped"] == 1

    second = client.post(
        "/v1/block-links/bulk",
        headers=headers,
        json={
            "source_block_id": "camarao_branco",
            "links": [
                {"target_block_id": "coentro", "weight": 2},
                {"target_block_id": "pimenta_malagueta", "weight": 3},
            ],
        },
    )
    assert second.status_code == 200, second.text
    assert second.json()["updated"] == 1
    assert second.json()["created"] == 1

    listed = client.get("/v1/block-links", params={"block_id": "camarao_branco"})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 3


def test_composition_edge_accepts_weight(client: TestClient):
    headers = _auth_headers(client)
    create = client.post(
        "/v1/compose/graphs",
        headers=headers,
        json={
            "title": "Com peso",
            "nodes": [
                {"id": "n1", "block_id": "carne_de_sol", "position": {"x": 0, "y": 0}},
                {"id": "n2", "block_id": "jerimum", "position": {"x": 200, "y": 0}},
            ],
            "edges": [
                {
                    "id": "e1",
                    "source": "n1",
                    "target": "n2",
                    "sourceHandle": "right",
                    "targetHandle": "left",
                    "weight": 3,
                }
            ],
        },
    )
    assert create.status_code == 201, create.text
    assert create.json()["edges"][0]["weight"] == 3
