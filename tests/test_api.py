"""Smoke tests da API (sem chamar LLM de geração completa)."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["library_version"] == "0.1.0"


def test_library_summary():
    response = client.get("/v1/library/summary")
    assert response.status_code == 200
    counts = response.json()["counts"]
    assert counts["flavor_blocks"] == 50
    assert counts["ingredients"] == 100


def test_list_flavor_blocks_filter():
    response = client.get("/v1/library/flavor_blocks", params={"q": "lagosta"})
    assert response.status_code == 200
    items = response.json()
    assert items
    assert any("lagosta" in item["id"] for item in items)


def test_get_ingredient():
    response = client.get("/v1/library/ingredients/sirigado")
    assert response.status_code == 200
    assert response.json()["id"] == "sirigado"


def test_compose_preview():
    response = client.post(
        "/v1/compose/preview",
        json={
            "objective": "Prato com lagosta",
            "ingredients": ["lagosta"],
            "servings": 4,
            "equipment": ["churrasqueira", "Thermomix TM7"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["protagonist_id"] == "lagosta_vermelha"
    assert body["blocks"]
    assert "architecture" in body
