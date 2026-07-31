"""Testes de ingredientes e estoque."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.main import app
from app.composition.ingredient_seed import seed_ingredients
from app.db.base import Base
from app.db.config import get_database_url
from app.db.session import configure_engine, get_db


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "ingredients.db"
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
            "email": "ing@laje.com",
            "password": "senha-forte",
            "firstName": "Chef",
            "lastName": "Ing",
        },
    )
    assert sign_up.status_code == 201, sign_up.text
    return {"Authorization": f"Bearer {sign_up.json()['accessToken']}"}


def test_seed_and_stock_status(client: TestClient):
    headers = _auth_headers(client)
    seeded = client.post("/v1/ingredients/seed", headers=headers)
    assert seeded.status_code == 200, seeded.text
    assert seeded.json()["created"] >= 100

    listed = client.get("/v1/ingredients", headers=headers, params={"q": "camarao"})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    item = listed.json()["items"][0]
    assert item["status"] == "out_of_stock"

    stocked = client.put(
        f"/v1/ingredients/{item['id']}/stock",
        headers=headers,
        json={"quantity": 500, "unit": "g", "reorder_level": 100},
    )
    assert stocked.status_code == 200
    assert stocked.json()["status"] == "in_stock"
    assert stocked.json()["stock_quantity"] == 500

    low = client.put(
        f"/v1/ingredients/{item['id']}/stock",
        headers=headers,
        json={"quantity": 50},
    )
    assert low.json()["status"] == "low_stock"

    missing = client.put(
        f"/v1/ingredients/{item['id']}/stock",
        headers=headers,
        json={"quantity": 0},
    )
    assert missing.json()["status"] == "out_of_stock"

    ordered = client.put(
        f"/v1/ingredients/{item['id']}/stock",
        headers=headers,
        json={"status_override": "on_order"},
    )
    assert ordered.json()["status"] == "on_order"


def test_create_inline_ingredient_and_use_in_recipe(client: TestClient):
    headers = _auth_headers(client)
    client.post("/v1/ingredients/seed", headers=headers)

    created = client.post(
        "/v1/ingredients",
        headers=headers,
        json={"name": "Pimenta biquinho", "category": "tempero", "default_unit": "g"},
    )
    assert created.status_code == 201, created.text
    ingredient_id = created.json()["id"]

    recipe = client.post(
        "/v1/recipes",
        headers=headers,
        json={
            "title": "Com ingredientes",
            "servings": 6,
            "block_ids": ["camarao_branco"],
            "ingredients": [
                {"ingredient_id": ingredient_id, "quantity": 20, "unit": "g"},
            ],
            "steps": [],
        },
    )
    assert recipe.status_code == 201, recipe.text
    body = recipe.json()
    assert body["servings"] == 6
    assert len(body["ingredients"]) == 1
    assert body["ingredients"][0]["quantity"] == 20
