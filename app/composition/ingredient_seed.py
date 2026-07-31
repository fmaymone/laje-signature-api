"""Seed de ingredientes a partir do catálogo + despensa comum."""

from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.composition.ingredient_units import default_unit_for_category
from app.db.models.ingredient import Ingredient

_LIBRARY_CATALOG = (
    Path(__file__).resolve().parent.parent.parent / "data" / "library" / "catalog" / "ingredients.yaml"
)

# Itens de despensa frequentes (além do catálogo nordestino).
EXTRA_PANTRY: list[dict] = [
    {"slug": "sal", "name": "Sal", "category": "tempero", "unit": "g", "aliases": ["sal refinado"]},
    {"slug": "acucar", "name": "Açúcar", "category": "seco", "unit": "g", "aliases": ["açúcar"]},
    {"slug": "acucar_mascavo", "name": "Açúcar mascavo", "category": "seco", "unit": "g"},
    {"slug": "farinha_de_trigo", "name": "Farinha de trigo", "category": "seco", "unit": "g"},
    {"slug": "farinha_de_mandioca", "name": "Farinha de mandioca", "category": "seco", "unit": "g"},
    {"slug": "ovo", "name": "Ovo", "category": "laticinio", "unit": "un", "aliases": ["ovos"]},
    {"slug": "leite", "name": "Leite", "category": "laticinio", "unit": "ml"},
    {"slug": "manteiga", "name": "Manteiga", "category": "gordura", "unit": "g"},
    {"slug": "azeite", "name": "Azeite", "category": "gordura", "unit": "ml", "aliases": ["azeite de oliva"]},
    {"slug": "oleo", "name": "Óleo", "category": "gordura", "unit": "ml"},
    {"slug": "alho", "name": "Alho", "category": "tempero", "unit": "dente"},
    {"slug": "cebola", "name": "Cebola", "category": "hortalica", "unit": "un"},
    {"slug": "tomate", "name": "Tomate", "category": "hortalica", "unit": "un"},
    {"slug": "pimenta_do_reino", "name": "Pimenta-do-reino", "category": "tempero", "unit": "g"},
    {"slug": "cominho", "name": "Cominho", "category": "tempero", "unit": "g"},
    {"slug": "colorau", "name": "Colorau", "category": "tempero", "unit": "g"},
    {"slug": "vinagre", "name": "Vinagre", "category": "condimento", "unit": "ml"},
    {"slug": "limao", "name": "Limão", "category": "fruta_acida", "unit": "un"},
    {"slug": "agua", "name": "Água", "category": "bebida", "unit": "ml"},
    {"slug": "arroz", "name": "Arroz", "category": "cereal", "unit": "g"},
    {"slug": "feijao", "name": "Feijão", "category": "leguminosa", "unit": "g"},
    {"slug": "batata", "name": "Batata", "category": "raiz_tuberculo", "unit": "g"},
    {"slug": "cenoura", "name": "Cenoura", "category": "hortalica", "unit": "g"},
    {"slug": "coentro_fresco", "name": "Coentro fresco", "category": "erva_aromatica", "unit": "ramo"},
    {"slug": "cebolinha", "name": "Cebolinha", "category": "erva_aromatica", "unit": "ramo"},
    {"slug": "salsa", "name": "Salsa", "category": "erva_aromatica", "unit": "ramo"},
    {"slug": "hortela", "name": "Hortelã", "category": "erva_aromatica", "unit": "folha"},
    {"slug": "gengibre", "name": "Gengibre", "category": "tempero", "unit": "g"},
    {"slug": "mel", "name": "Mel", "category": "seco", "unit": "ml"},
    {"slug": "creme_de_leite", "name": "Creme de leite", "category": "laticinio", "unit": "ml"},
]


def _load_catalog() -> list[dict]:
    if not _LIBRARY_CATALOG.exists():
        return []
    data = yaml.safe_load(_LIBRARY_CATALOG.read_text(encoding="utf-8")) or {}
    return list(data.get("ingredients") or [])


def seed_ingredients(db: Session) -> dict[str, int]:
    """Idempotente: cria ingredientes do catálogo + despensa se ainda não existirem."""
    existing_slugs = set(db.scalars(select(Ingredient.slug)).all())
    created = 0
    skipped = 0

    for item in _load_catalog():
        slug = str(item.get("id") or "").strip()
        if not slug:
            continue
        if slug in existing_slugs:
            skipped += 1
            continue
        category = str(item.get("category") or "outro")
        row = Ingredient(
            slug=slug,
            name=str(item.get("name") or slug),
            aliases=list(item.get("aliases") or []),
            category=category,
            default_unit=default_unit_for_category(category),
            notes=item.get("notes"),
            is_system=True,
        )
        db.add(row)
        existing_slugs.add(slug)
        created += 1

    for item in EXTRA_PANTRY:
        slug = item["slug"]
        if slug in existing_slugs:
            skipped += 1
            continue
        row = Ingredient(
            slug=slug,
            name=item["name"],
            aliases=list(item.get("aliases") or []),
            category=item.get("category") or "outro",
            default_unit=item.get("unit") or "g",
            notes=None,
            is_system=True,
        )
        db.add(row)
        existing_slugs.add(slug)
        created += 1

    if created:
        db.commit()
    return {"created": created, "skipped": skipped, "total": len(existing_slugs)}
