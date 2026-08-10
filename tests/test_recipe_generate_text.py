"""Testes de geração de receita a partir de texto."""

from __future__ import annotations

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
    get_or_create_ingredient,
    resolve_draft_ingredients,
)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "recipe_generate.db"
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


def _auth_headers(client: TestClient, email: str = "generate@laje.com") -> dict[str, str]:
    sign_up = client.post(
        "/api/auth/sign-up",
        json={
            "email": email,
            "password": "senha-forte",
            "firstName": "Chef",
            "lastName": "Generate",
        },
    )
    assert sign_up.status_code == 201, sign_up.text
    return {"Authorization": f"Bearer {sign_up.json()['accessToken']}"}


def _sample_draft() -> RecipeImageImportDraft:
    return RecipeImageImportDraft(
        title="Molho caseiro estilo Big Mac",
        notes="Versão caseira",
        servings=4,
        ingredients=[
            RecipeImageIngredientLine(name="Maionese", quantity=120, unit="g"),
            RecipeImageIngredientLine(name="TOMATE", quantity=30, unit="g"),
            RecipeImageIngredientLine(name="tomate", quantity=10, unit="g"),
        ],
        lanes=[RecipeLane(id="main", name="Principal")],
        steps=[
            RecipeStep(
                id="s1",
                process="misturar",
                description="Misturar os ingredientes",
                time_before_service_minutes=0,
                duration_minutes=10,
                lane_id="main",
            )
        ],
        warnings=["Assumi molho estilo Big Mac caseiro"],
    )


def test_case_insensitive_ingredient_match(client: TestClient):
    headers = _auth_headers(client)
    # Nome único fora do seed para isolar o match case/acento
    created = client.post(
        "/v1/ingredients",
        headers=headers,
        json={"name": "Pimentão Amarelo Especial", "category": "hortalica", "default_unit": "g"},
    )
    assert created.status_code == 201, created.text
    ingredient_id = created.json()["id"]

    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "generate@laje.com").one()
        for variant in (
            "PIMENTÃO AMARELO ESPECIAL",
            "pimentao amarelo especial",
            "Pimentão Amarelo Especial",
        ):
            found = find_ingredient_by_name(db, variant)
            assert found is not None, variant
            assert str(found.id) == ingredient_id

        draft = RecipeImageImportDraft(
            title="Teste",
            servings=2,
            ingredients=[
                RecipeImageIngredientLine(
                    name="PIMENTÃO AMARELO ESPECIAL", quantity=50, unit="g"
                ),
                RecipeImageIngredientLine(
                    name="pimentao amarelo especial", quantity=20, unit="g"
                ),
            ],
        )
        lines, created_names = resolve_draft_ingredients(db, draft=draft, user=user)
        assert created_names == []
        assert len(lines) == 1
        assert str(lines[0].ingredient_id) == ingredient_id
    finally:
        db.close()


def test_get_or_create_does_not_duplicate_case(client: TestClient):
    headers = _auth_headers(client)
    created = client.post(
        "/v1/ingredients",
        headers=headers,
        json={"name": "Cebola Roxa Única", "category": "hortalica", "default_unit": "g"},
    )
    assert created.status_code == 201, created.text

    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "generate@laje.com").one()
        line = RecipeImageIngredientLine(name="CEBOLA ROXA UNICA", quantity=1, unit="g")
        first, created1 = get_or_create_ingredient(db, line=line, user=user)
        second, created2 = get_or_create_ingredient(db, line=line, user=user)
        assert created1 is False
        assert created2 is False
        assert first.id == second.id
        db.commit()
    finally:
        db.close()


def test_generate_from_text_endpoint_mocked(client: TestClient):
    headers = _auth_headers(client)
    client.post(
        "/v1/ingredients",
        headers=headers,
        json={"name": "Tomate", "category": "hortalica", "default_unit": "g"},
    )
    draft = _sample_draft()

    with patch(
        "api.routes.recipes_import.generate_recipe_from_text",
        return_value=draft,
    ) as mocked:
        res = client.post(
            "/v1/recipes/generate-from-text",
            headers=headers,
            json={"prompt": "Quero um molho caseiro de big mac"},
        )
        assert res.status_code == 200, res.text
        mocked.assert_called_once()
        body = res.json()
        assert body["title"] == "Molho caseiro estilo Big Mac"
        assert body["block_ids"] == []
        assert len(body["ingredients"]) == 2  # TOMATE + tomate collapsed
        tomato_lines = body["ingredients"]
        assert all("ingredient_id" in line for line in tomato_lines)
        assert "Assumi" in body["warnings"][0] or len(body["warnings"]) >= 1


def test_generate_from_text_empty_prompt(client: TestClient):
    headers = _auth_headers(client)
    res = client.post(
        "/v1/recipes/generate-from-text",
        headers=headers,
        json={"prompt": "   "},
    )
    assert res.status_code == 422


def test_generate_from_text_requires_auth(client: TestClient):
    res = client.post(
        "/v1/recipes/generate-from-text",
        json={"prompt": "molho"},
    )
    assert res.status_code in (401, 403)
