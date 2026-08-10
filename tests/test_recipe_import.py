"""Testes de importação de receita a partir de imagem."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.main import app
from api.schemas_recipe_import import (
    RecipeImageImportDraft,
    RecipeImageIngredientLine,
)
from api.schemas_recipes_persist import RecipeLane, RecipeStep
from app.db.base import Base
from app.db.config import get_database_url
from app.db.models import User
from app.db.session import configure_engine, get_db
from app.ingredient_resolve import (
    find_ingredient_by_name,
    resolve_draft_ingredients,
    slugify_ingredient,
)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "recipe_import.db"
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


def _auth_headers(client: TestClient, email: str = "import@laje.com") -> dict[str, str]:
    sign_up = client.post(
        "/api/auth/sign-up",
        json={
            "email": email,
            "password": "senha-forte",
            "firstName": "Chef",
            "lastName": "Import",
        },
    )
    assert sign_up.status_code == 201, sign_up.text
    return {"Authorization": f"Bearer {sign_up.json()['accessToken']}"}


def _sample_draft() -> RecipeImageImportDraft:
    return RecipeImageImportDraft(
        title="Moqueca de camarão",
        notes="Do print da vovó",
        servings=4,
        ingredients=[
            RecipeImageIngredientLine(name="Camarão branco", quantity=500, unit="g"),
            RecipeImageIngredientLine(name="Pimenta biquinho especial", quantity=20, unit="g"),
            RecipeImageIngredientLine(name="Coentro", quantity=1, unit="ramo"),
        ],
        lanes=[RecipeLane(id="main", name="Principal")],
        steps=[
            RecipeStep(
                id="s1",
                process="refogar",
                description="Refogar o camarão",
                time_before_service_minutes=30,
                duration_minutes=15,
                lane_id="main",
            )
        ],
        warnings=["Tempo de cozimento parcialmente ilegível"],
    )


def test_slugify_ingredient():
    assert slugify_ingredient("Camarão Branco") == "camarao_branco"
    assert slugify_ingredient("  Pimentão  ") == "pimentao"


def test_resolve_match_and_create(client: TestClient):
    headers = _auth_headers(client)
    client.post("/v1/ingredients/seed", headers=headers)

    # ensure seeded camarão exists
    listed = client.get("/v1/ingredients", headers=headers, params={"q": "camarão"})
    assert listed.status_code == 200

    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "import@laje.com").one()
        draft = _sample_draft()
        lines, created = resolve_draft_ingredients(db, draft=draft, user=user)
        assert len(lines) == 3
        assert "Pimenta biquinho especial" in created
        # camarão / coentro must match seed when present
        names_created_lower = {n.lower() for n in created}
        assert "pimenta biquinho especial" in names_created_lower

        matched = find_ingredient_by_name(db, "Camarão branco")
        assert matched is not None
        created_row = find_ingredient_by_name(db, "Pimenta biquinho especial")
        assert created_row is not None
        assert created_row.is_system is False
    finally:
        db.close()


def test_import_from_image_endpoint_mocked(client: TestClient):
    headers = _auth_headers(client)
    client.post("/v1/ingredients/seed", headers=headers)
    draft = _sample_draft()

    with patch(
        "api.routes.recipes_import.parse_recipe_from_image",
        return_value=draft,
    ) as mocked:
        files = {"file": ("receita.png", BytesIO(b"fake-png-bytes"), "image/png")}
        res = client.post(
            "/v1/recipes/import-from-image",
            headers=headers,
            files=files,
        )
        assert res.status_code == 200, res.text
        mocked.assert_called_once()
        body = res.json()
        assert body["title"] == "Moqueca de camarão"
        assert body["servings"] == 4
        assert body["block_ids"] == []
        assert body["composition_id"] is None
        assert len(body["ingredients"]) == 3
        assert all("ingredient_id" in line for line in body["ingredients"])
        assert body["steps"][0]["process"] == "refogar"
        assert "Pimenta biquinho especial" in body["created_ingredient_names"]
        assert "ilegível" in body["warnings"][0].lower() or len(body["warnings"]) >= 1

        # create recipe with returned payload
        create = client.post(
            "/v1/recipes",
            headers=headers,
            json={
                "title": body["title"],
                "notes": body["notes"],
                "servings": body["servings"],
                "block_ids": body["block_ids"],
                "ingredients": body["ingredients"],
                "lanes": body["lanes"],
                "steps": body["steps"],
            },
        )
        assert create.status_code == 201, create.text


def test_import_rejects_invalid_type(client: TestClient):
    headers = _auth_headers(client)
    files = {"file": ("notes.txt", BytesIO(b"not an image"), "text/plain")}
    res = client.post(
        "/v1/recipes/import-from-image",
        headers=headers,
        files=files,
    )
    assert res.status_code == 400
    assert "JPEG" in res.json()["detail"] or "imagem" in res.json()["detail"].lower()


def test_import_rejects_oversized(client: TestClient, monkeypatch):
    headers = _auth_headers(client)
    monkeypatch.setattr("api.routes.recipes_import.MAX_BYTES", 10)
    files = {"file": ("big.png", BytesIO(b"01234567890123456789"), "image/png")}
    res = client.post(
        "/v1/recipes/import-from-image",
        headers=headers,
        files=files,
    )
    assert res.status_code == 400
    assert "8 MB" in res.json()["detail"] or "maior" in res.json()["detail"].lower()


def test_import_requires_auth(client: TestClient):
    files = {"file": ("receita.png", BytesIO(b"x"), "image/png")}
    res = client.post("/v1/recipes/import-from-image", files=files)
    assert res.status_code in (401, 403)
