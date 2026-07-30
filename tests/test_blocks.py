"""CRUD de blocos de sabor (merge catálogo + DB)."""

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
    db_file = tmp_path / "blocks.db"
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
            "email": "blocks@laje.com",
            "password": "senha-forte",
            "firstName": "Chef",
            "lastName": "Blocos",
        },
    )
    assert sign_up.status_code == 201, sign_up.text
    return {"Authorization": f"Bearer {sign_up.json()['accessToken']}"}


def test_list_blocks_includes_catalog(client: TestClient):
    response = client.get("/v1/blocks")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 100
    assert any(item["id"] == "carne_de_sol" for item in body["items"])


def test_create_update_delete_custom_block(client: TestClient):
    headers = _auth_headers(client)

    create = client.post(
        "/v1/blocks",
        headers=headers,
        json={
            "id": "teste_atomico",
            "name": "Teste Atômico",
            "family": "sertão",
            "ingredient_ids": ["teste_atomico"],
            "culinary_roles": ["base"],
            "compatible_protagonists": ["carne_de_sol"],
            "recommended_base_ids": [],
            "target_sensory_profile": {
                "acidity": 3,
                "saltiness": 2,
                "sweetness": 1,
                "bitterness": 0,
                "umami": 4,
                "fat": 2,
                "heat": 0,
                "aroma": 5,
                "freshness": 3,
            },
            "texture_targets": ["cremoso"],
            "notes": "bloco de teste",
        },
    )
    assert create.status_code == 201, create.text
    assert create.json()["origin"] == "custom"

    updated = client.put(
        "/v1/blocks/teste_atomico",
        headers=headers,
        json={"name": "Teste Atômico 2", "notes": "editado"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Teste Atômico 2"

    deleted = client.delete("/v1/blocks/teste_atomico", headers=headers)
    assert deleted.status_code == 204

    missing = client.get("/v1/blocks/teste_atomico")
    assert missing.status_code == 404


def test_override_catalog_block(client: TestClient):
    headers = _auth_headers(client)
    updated = client.put(
        "/v1/blocks/carne_de_sol",
        headers=headers,
        json={"notes": "override local"},
    )
    assert updated.status_code == 200
    assert updated.json()["origin"] == "override"
    assert updated.json()["notes"] == "override local"

    # deleting override restores catalog
    deleted = client.delete("/v1/blocks/carne_de_sol", headers=headers)
    assert deleted.status_code == 204
    restored = client.get("/v1/blocks/carne_de_sol")
    assert restored.status_code == 200
    assert restored.json()["origin"] == "catalog"
