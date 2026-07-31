"""CRUD de ingredientes + estoque por usuário."""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.routes.auth import get_current_user
from api.schemas_ingredients import (
    IngredientCreate,
    IngredientListResponse,
    IngredientRead,
    IngredientSeedResponse,
    IngredientStockPatch,
    IngredientUpdate,
)
from app.composition.ingredient_seed import seed_ingredients
from app.composition.ingredient_units import compute_stock_status
from app.db.models import Ingredient, IngredientStock, User
from app.db.session import get_db

router = APIRouter(prefix="/v1/ingredients", tags=["ingredients"])


def _slugify(value: str) -> str:
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


def _stock_map(db: Session, user: User) -> dict[uuid.UUID, IngredientStock]:
    rows = db.scalars(select(IngredientStock).where(IngredientStock.owner_id == user.id)).all()
    return {row.ingredient_id: row for row in rows}


def _to_read(item: Ingredient, stock: IngredientStock | None) -> IngredientRead:
    quantity = float(stock.quantity) if stock else 0.0
    reorder = float(stock.reorder_level) if stock else 0.0
    override = stock.status_override if stock else None
    return IngredientRead(
        id=item.id,
        slug=item.slug,
        name=item.name,
        aliases=list(item.aliases or []),
        category=item.category,
        default_unit=item.default_unit,
        notes=item.notes,
        is_system=bool(item.is_system),
        stock_quantity=quantity,
        stock_unit=stock.unit if stock else item.default_unit,
        reorder_level=reorder,
        status=compute_stock_status(quantity, reorder, override),  # type: ignore[arg-type]
        status_override=override,  # type: ignore[arg-type]
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _ensure_seeded(db: Session) -> None:
    count = db.scalar(select(func.count()).select_from(Ingredient)) or 0
    if count == 0:
        seed_ingredients(db)


@router.post("/seed", response_model=IngredientSeedResponse)
def run_seed(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> IngredientSeedResponse:
    _ = user
    result = seed_ingredients(db)
    return IngredientSeedResponse(**result)


@router.get("", response_model=IngredientListResponse)
@router.get("/", response_model=IngredientListResponse, include_in_schema=False)
def list_ingredients(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
) -> IngredientListResponse:
    _ensure_seeded(db)
    stmt = select(Ingredient)
    if category:
        stmt = stmt.where(Ingredient.category == category)
    if q:
        needle = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Ingredient.name).like(needle),
                func.lower(Ingredient.slug).like(needle),
            )
        )
    items = list(db.scalars(stmt.order_by(Ingredient.name.asc())).all())
    stocks = _stock_map(db, user)
    reads = [_to_read(item, stocks.get(item.id)) for item in items]
    if status_filter:
        reads = [item for item in reads if item.status == status_filter]
    total = len(reads)
    page = reads[skip : skip + limit]
    return IngredientListResponse(items=page, total=total)


@router.post("", response_model=IngredientRead, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=IngredientRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_ingredient(
    payload: IngredientCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> IngredientRead:
    _ensure_seeded(db)
    slug = _slugify(payload.slug or payload.name)
    row = Ingredient(
        slug=slug,
        name=payload.name.strip(),
        aliases=payload.aliases,
        category=payload.category.strip() or "outro",
        default_unit=payload.default_unit,
        notes=payload.notes,
        is_system=False,
        created_by=user.id,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Já existe um ingrediente com este id.") from exc
    db.refresh(row)
    return _to_read(row, None)


@router.get("/{ingredient_id}", response_model=IngredientRead)
def get_ingredient(
    ingredient_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> IngredientRead:
    _ensure_seeded(db)
    item = db.get(Ingredient, ingredient_id)
    if not item:
        raise HTTPException(status_code=404, detail="Ingrediente não encontrado.")
    stock = db.scalar(
        select(IngredientStock).where(
            IngredientStock.owner_id == user.id,
            IngredientStock.ingredient_id == ingredient_id,
        )
    )
    return _to_read(item, stock)


@router.put("/{ingredient_id}", response_model=IngredientRead)
def update_ingredient(
    ingredient_id: uuid.UUID,
    payload: IngredientUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> IngredientRead:
    item = db.get(Ingredient, ingredient_id)
    if not item:
        raise HTTPException(status_code=404, detail="Ingrediente não encontrado.")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(item, key, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    stock = db.scalar(
        select(IngredientStock).where(
            IngredientStock.owner_id == user.id,
            IngredientStock.ingredient_id == ingredient_id,
        )
    )
    return _to_read(item, stock)


@router.put("/{ingredient_id}/stock", response_model=IngredientRead)
def upsert_stock(
    ingredient_id: uuid.UUID,
    payload: IngredientStockPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> IngredientRead:
    item = db.get(Ingredient, ingredient_id)
    if not item:
        raise HTTPException(status_code=404, detail="Ingrediente não encontrado.")

    stock = db.scalar(
        select(IngredientStock).where(
            IngredientStock.owner_id == user.id,
            IngredientStock.ingredient_id == ingredient_id,
        )
    )
    if stock is None:
        stock = IngredientStock(
            owner_id=user.id,
            ingredient_id=ingredient_id,
            quantity=0,
            unit=item.default_unit,
            reorder_level=0,
        )
        db.add(stock)

    data = payload.model_dump(exclude_unset=True)
    if "quantity" in data and data["quantity"] is not None:
        stock.quantity = float(data["quantity"])
    if "unit" in data and data["unit"] is not None:
        stock.unit = data["unit"]
    if "reorder_level" in data and data["reorder_level"] is not None:
        stock.reorder_level = float(data["reorder_level"])
    if data.get("clear_status_override"):
        stock.status_override = None
    elif "status_override" in data:
        stock.status_override = data["status_override"]
    if "notes" in data:
        stock.notes = data["notes"]

    db.add(stock)
    db.commit()
    db.refresh(stock)
    db.refresh(item)
    return _to_read(item, stock)


@router.delete("/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(
    ingredient_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    _ = user
    item = db.get(Ingredient, ingredient_id)
    if not item:
        raise HTTPException(status_code=404, detail="Ingrediente não encontrado.")
    if item.is_system:
        raise HTTPException(
            status_code=400,
            detail="Ingredientes do sistema não podem ser excluídos.",
        )
    db.delete(item)
    db.commit()
