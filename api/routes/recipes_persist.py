"""CRUD de receitas persistidas (blocos + passos + composição opcional)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from api.routes.auth import get_current_user
from api.schemas_recipes_persist import (
    RecipeCreate,
    RecipeListResponse,
    RecipeRead,
    RecipeUpdate,
)
from app.composition.blocks_store import get_merged_flavor_block
from app.db.models import CompositionGraph, Ingredient, Recipe, User
from app.db.session import get_db

router = APIRouter(prefix="/v1/recipes", tags=["recipe-records"])


def _dump_steps(steps) -> list[dict]:
    return [step.model_dump() for step in steps]


def _dump_ingredients(lines) -> list[dict]:
    return [line.model_dump(mode="json") for line in lines]


def _normalize_ingredients(lines, db: Session) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    for line in lines:
        ingredient_id = line.ingredient_id if hasattr(line, "ingredient_id") else line["ingredient_id"]
        key = str(ingredient_id)
        if key in seen:
            continue
        if db.get(Ingredient, ingredient_id) is None:
            raise HTTPException(
                status_code=400,
                detail=f"Ingrediente '{ingredient_id}' não encontrado.",
            )
        seen.add(key)
        dumped = line.model_dump(mode="json") if hasattr(line, "model_dump") else dict(line)
        result.append(dumped)
    return result


def _normalize_block_ids(block_ids: list[str], db: Session) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in block_ids:
        block_id = raw.strip()
        if not block_id or block_id in seen:
            continue
        if get_merged_flavor_block(block_id, db) is None:
            raise HTTPException(
                status_code=400,
                detail=f"Bloco '{block_id}' não encontrado.",
            )
        seen.add(block_id)
        result.append(block_id)
    return result


def _validate_composition(
    db: Session,
    composition_id: uuid.UUID | None,
    user: User,
) -> uuid.UUID | None:
    if composition_id is None:
        return None
    graph = db.get(CompositionGraph, composition_id)
    if not graph or graph.owner_id != user.id:
        raise HTTPException(
            status_code=400,
            detail="Composição não encontrada ou não pertence a você.",
        )
    return composition_id


def _get_owned_recipe(db: Session, recipe_id: uuid.UUID, user: User) -> Recipe:
    recipe = db.get(Recipe, recipe_id)
    if not recipe or recipe.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receita não encontrada.")
    return recipe


@router.post("", response_model=RecipeRead, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=RecipeRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_recipe(
    payload: RecipeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Recipe:
    composition_id = _validate_composition(db, payload.composition_id, user)
    block_ids = _normalize_block_ids(payload.block_ids, db)
    ingredients = _normalize_ingredients(payload.ingredients, db)
    recipe = Recipe(
        title=payload.title.strip() or "Receita",
        notes=payload.notes,
        owner_id=user.id,
        composition_id=composition_id,
        servings=payload.servings,
        block_ids=block_ids,
        ingredients=ingredients,
        steps=_dump_steps(payload.steps),
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.get("", response_model=RecipeListResponse)
@router.get("/", response_model=RecipeListResponse, include_in_schema=False)
def list_recipes(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> RecipeListResponse:
    owned = Recipe.owner_id == user.id
    total = db.scalar(select(func.count()).select_from(Recipe).where(owned)) or 0
    items = db.scalars(
        select(Recipe).where(owned).order_by(Recipe.updated_at.desc()).offset(skip).limit(limit)
    ).all()
    return RecipeListResponse(items=list(items), total=total)


@router.get("/{recipe_id}", response_model=RecipeRead)
def get_recipe(
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Recipe:
    return _get_owned_recipe(db, recipe_id, user)


@router.put("/{recipe_id}", response_model=RecipeRead)
def update_recipe(
    recipe_id: uuid.UUID,
    payload: RecipeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Recipe:
    recipe = _get_owned_recipe(db, recipe_id, user)
    data = payload.model_dump(exclude_unset=True)

    if "title" in data and data["title"] is not None:
        recipe.title = data["title"].strip() or recipe.title
    if "notes" in data:
        recipe.notes = data["notes"]
    if "composition_id" in data:
        recipe.composition_id = _validate_composition(db, data["composition_id"], user)
    if "servings" in data and data["servings"] is not None:
        recipe.servings = int(data["servings"])
    if "block_ids" in data and data["block_ids"] is not None:
        recipe.block_ids = _normalize_block_ids(data["block_ids"], db)
        flag_modified(recipe, "block_ids")
    if "ingredients" in data and data["ingredients"] is not None:
        recipe.ingredients = _normalize_ingredients(payload.ingredients or [], db)
        flag_modified(recipe, "ingredients")
    if "steps" in data and data["steps"] is not None:
        recipe.steps = data["steps"]
        flag_modified(recipe, "steps")

    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    recipe = _get_owned_recipe(db, recipe_id, user)
    db.delete(recipe)
    db.commit()
