"""Resolve nomes de ingredientes do import/generate para o catálogo (match ou cria)."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.schemas_recipe_import import RecipeImageIngredientLine, RecipeImageImportDraft
from api.schemas_recipes_persist import RecipeIngredientLine
from app.composition.ingredient_seed import seed_ingredients
from app.db.models import Ingredient, User


def slugify_ingredient(value: str) -> str:
    text = value.strip().lower()
    table = str.maketrans(
        {
            "á": "a",
            "ã": "a",
            "â": "a",
            "à": "a",
            "é": "e",
            "ê": "e",
            "í": "i",
            "ó": "o",
            "ô": "o",
            "õ": "o",
            "ú": "u",
            "ç": "c",
        }
    )
    text = text.translate(table)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")[:120] or "ingrediente"


def normalize_ingredient_display_name(value: str) -> str:
    """Nome legível ao criar: strip + capitalização simples da primeira letra."""
    text = " ".join(value.strip().split())
    if not text:
        return "Ingrediente"
    return text[0].upper() + text[1:] if len(text) > 1 else text.upper()


def _ensure_seeded(db: Session) -> None:
    count = db.scalar(select(func.count()).select_from(Ingredient)) or 0
    if count == 0:
        seed_ingredients(db)


def find_ingredient_by_name(db: Session, name: str) -> Ingredient | None:
    cleaned = name.strip()
    if not cleaned:
        return None
    slug = slugify_ingredient(cleaned)

    by_slug = db.scalar(select(Ingredient).where(Ingredient.slug == slug))
    if by_slug:
        return by_slug

    by_name = db.scalar(
        select(Ingredient).where(func.lower(Ingredient.name) == cleaned.lower())
    )
    if by_name:
        return by_name

    # Scan: slugify(name) e aliases (case/acento-insensitive)
    for item in db.scalars(select(Ingredient)).all():
        if slugify_ingredient(item.name) == slug:
            return item
        for alias in item.aliases or []:
            if not isinstance(alias, str):
                continue
            if alias.strip().lower() == cleaned.lower() or slugify_ingredient(alias) == slug:
                return item
    return None


def _unique_slug(db: Session, base: str) -> str:
    slug = base
    n = 2
    while db.scalar(select(Ingredient).where(Ingredient.slug == slug)) is not None:
        suffix = f"_{n}"
        slug = f"{base[: 120 - len(suffix)]}{suffix}"
        n += 1
    return slug


def get_or_create_ingredient(
    db: Session,
    *,
    line: RecipeImageIngredientLine,
    user: User,
) -> tuple[Ingredient, bool]:
    """Retorna (ingredient, created). Em match, preserva o nome do catálogo."""
    existing = find_ingredient_by_name(db, line.name)
    if existing:
        return existing, False
    display = normalize_ingredient_display_name(line.name)
    slug = _unique_slug(db, slugify_ingredient(display))
    row = Ingredient(
        id=uuid.uuid4(),
        slug=slug,
        name=display,
        aliases=[],
        category="outro",
        default_unit=line.unit,
        notes=None,
        is_system=False,
        created_by=user.id,
    )
    db.add(row)
    db.flush()
    return row, True


def list_catalog_names(db: Session, *, limit: int = 200) -> list[str]:
    _ensure_seeded(db)
    rows = db.scalars(select(Ingredient.name).order_by(Ingredient.name.asc()).limit(limit)).all()
    return [str(name) for name in rows]


def resolve_draft_ingredients(
    db: Session,
    *,
    draft: RecipeImageImportDraft,
    user: User,
) -> tuple[list[RecipeIngredientLine], list[str]]:
    """Converte linhas por nome em RecipeIngredientLine; cria faltantes.

    Returns:
        (lines, created_names)
    """
    _ensure_seeded(db)
    lines: list[RecipeIngredientLine] = []
    created_names: list[str] = []
    seen_ids: set[uuid.UUID] = set()

    for raw in draft.ingredients:
        ingredient, created = get_or_create_ingredient(db, line=raw, user=user)
        if created:
            created_names.append(ingredient.name)
        if ingredient.id in seen_ids:
            continue
        seen_ids.add(ingredient.id)
        lines.append(
            RecipeIngredientLine(
                ingredient_id=ingredient.id,
                quantity=raw.quantity,
                unit=raw.unit,
                notes=raw.notes,
            )
        )

    db.commit()
    return lines, created_names
