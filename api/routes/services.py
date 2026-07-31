"""CRUD de serviços (nome + receitas + data)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from api.routes.auth import get_current_user
from api.schemas_services import (
    ServiceCreate,
    ServiceListResponse,
    ServiceRead,
    ServiceUpdate,
)
from app.db.models import Recipe, Service, User
from app.db.session import get_db

router = APIRouter(prefix="/v1/services", tags=["services"])


def _normalize_recipe_ids(
    recipe_ids: list[uuid.UUID],
    db: Session,
    user: User,
) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for recipe_id in recipe_ids:
        key = str(recipe_id)
        if key in seen:
            continue
        recipe = db.get(Recipe, recipe_id)
        if not recipe or recipe.owner_id != user.id:
            raise HTTPException(
                status_code=400,
                detail=f"Receita '{recipe_id}' não encontrada ou não pertence a você.",
            )
        seen.add(key)
        result.append(key)
    return result


def _to_read(row: Service) -> ServiceRead:
    recipe_ids: list[uuid.UUID] = []
    for raw in row.recipe_ids or []:
        try:
            recipe_ids.append(uuid.UUID(str(raw)))
        except ValueError:
            continue
    return ServiceRead(
        id=row.id,
        name=row.name,
        notes=row.notes,
        owner_id=row.owner_id,
        service_date=row.service_date,
        recipe_ids=recipe_ids,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _get_owned_service(db: Session, service_id: uuid.UUID, user: User) -> Service:
    service = db.get(Service, service_id)
    if not service or service.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serviço não encontrado.")
    return service


@router.post("", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ServiceRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_service(
    payload: ServiceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ServiceRead:
    recipe_ids = _normalize_recipe_ids(payload.recipe_ids, db, user)
    service = Service(
        name=payload.name.strip() or "Serviço",
        notes=payload.notes,
        owner_id=user.id,
        service_date=payload.service_date,
        recipe_ids=recipe_ids,
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return _to_read(service)


@router.get("", response_model=ServiceListResponse)
@router.get("/", response_model=ServiceListResponse, include_in_schema=False)
def list_services(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> ServiceListResponse:
    owned = Service.owner_id == user.id
    total = db.scalar(select(func.count()).select_from(Service).where(owned)) or 0
    items = db.scalars(
        select(Service)
        .where(owned)
        .order_by(Service.service_date.desc(), Service.updated_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return ServiceListResponse(items=[_to_read(item) for item in items], total=total)


@router.get("/{service_id}", response_model=ServiceRead)
def get_service(
    service_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ServiceRead:
    return _to_read(_get_owned_service(db, service_id, user))


@router.put("/{service_id}", response_model=ServiceRead)
def update_service(
    service_id: uuid.UUID,
    payload: ServiceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ServiceRead:
    service = _get_owned_service(db, service_id, user)
    data = payload.model_dump(exclude_unset=True)

    if "name" in data and data["name"] is not None:
        service.name = data["name"].strip() or service.name
    if "notes" in data:
        service.notes = data["notes"]
    if "service_date" in data and data["service_date"] is not None:
        service.service_date = data["service_date"]
    if "recipe_ids" in data and data["recipe_ids"] is not None:
        service.recipe_ids = _normalize_recipe_ids(data["recipe_ids"], db, user)
        flag_modified(service, "recipe_ids")

    db.add(service)
    db.commit()
    db.refresh(service)
    return _to_read(service)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    service = _get_owned_service(db, service_id, user)
    db.delete(service)
    db.commit()
