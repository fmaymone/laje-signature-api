"""CRUD de ligações ponderadas entre blocos (peso 1–3)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.routes.auth import get_current_user
from api.schemas_block_links import (
    BlockLinkBulkCreate,
    BlockLinkBulkResult,
    BlockLinkCreate,
    BlockLinkListResponse,
    BlockLinkRead,
    BlockLinkUpdate,
)
from app.composition.blocks_store import get_merged_flavor_block
from app.db.models import BlockLink, User
from app.db.session import get_db

router = APIRouter(prefix="/v1/block-links", tags=["block-links"])


def _ensure_block_exists(db: Session, block_id: str) -> None:
    if get_merged_flavor_block(block_id, db) is None:
        raise HTTPException(status_code=400, detail=f"Bloco '{block_id}' não encontrado.")


@router.get("", response_model=BlockLinkListResponse)
@router.get("/", response_model=BlockLinkListResponse, include_in_schema=False)
def list_block_links(
    db: Session = Depends(get_db),
    block_id: str | None = Query(
        default=None,
        description="Filtra ligações onde o bloco é origem ou destino",
    ),
    min_weight: int | None = Query(default=None, ge=1, le=3),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> BlockLinkListResponse:
    stmt = select(BlockLink)
    count_stmt = select(func.count()).select_from(BlockLink)

    if block_id:
        filt = or_(
            BlockLink.source_block_id == block_id,
            BlockLink.target_block_id == block_id,
        )
        stmt = stmt.where(filt)
        count_stmt = count_stmt.where(filt)
    if min_weight is not None:
        stmt = stmt.where(BlockLink.weight >= min_weight)
        count_stmt = count_stmt.where(BlockLink.weight >= min_weight)

    total = db.scalar(count_stmt) or 0
    items = db.scalars(
        stmt.order_by(BlockLink.weight.desc(), BlockLink.updated_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return BlockLinkListResponse(items=list(items), total=total)


@router.get("/{link_id}", response_model=BlockLinkRead)
def get_block_link(link_id: uuid.UUID, db: Session = Depends(get_db)) -> BlockLink:
    link = db.get(BlockLink, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Ligação não encontrada.")
    return link


@router.post("", response_model=BlockLinkRead, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=BlockLinkRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_block_link(
    payload: BlockLinkCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BlockLink:
    source = payload.source_block_id.strip()
    target = payload.target_block_id.strip()
    _ensure_block_exists(db, source)
    _ensure_block_exists(db, target)

    link = BlockLink(
        source_block_id=source,
        target_block_id=target,
        weight=int(payload.weight),
        notes=payload.notes,
        created_by=user.id,
    )
    db.add(link)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Já existe ligação entre estes blocos (nesta direção).",
        ) from exc
    db.refresh(link)
    return link


@router.post("/bulk", response_model=BlockLinkBulkResult)
@router.post("/bulk/", response_model=BlockLinkBulkResult, include_in_schema=False)
def bulk_upsert_block_links(
    payload: BlockLinkBulkCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BlockLinkBulkResult:
    """Cria ou atualiza várias combinações a partir de um bloco (estilo Flavor Bible)."""
    source = payload.source_block_id.strip()
    _ensure_block_exists(db, source)

    created = 0
    updated = 0
    skipped = 0
    results: list[BlockLink] = []
    seen_targets: set[str] = set()

    for item in payload.links:
        target = item.target_block_id.strip()
        if not target or target == source or target in seen_targets:
            skipped += 1
            continue
        seen_targets.add(target)

        if get_merged_flavor_block(target, db) is None:
            skipped += 1
            continue

        existing = db.scalar(
            select(BlockLink).where(
                BlockLink.source_block_id == source,
                BlockLink.target_block_id == target,
            )
        )
        if existing is None:
            link = BlockLink(
                source_block_id=source,
                target_block_id=target,
                weight=int(item.weight),
                notes=item.notes,
                created_by=user.id,
            )
            db.add(link)
            results.append(link)
            created += 1
        else:
            existing.weight = int(item.weight)
            if item.notes is not None:
                existing.notes = item.notes
            db.add(existing)
            results.append(existing)
            updated += 1

    db.commit()
    for link in results:
        db.refresh(link)

    return BlockLinkBulkResult(
        created=created,
        updated=updated,
        skipped=skipped,
        items=results,
    )


@router.put("/{link_id}", response_model=BlockLinkRead)
def update_block_link(
    link_id: uuid.UUID,
    payload: BlockLinkUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BlockLink:
    _ = user
    link = db.get(BlockLink, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Ligação não encontrada.")

    data = payload.model_dump(exclude_unset=True)
    if "weight" in data and data["weight"] is not None:
        link.weight = int(data["weight"])
    if "notes" in data:
        link.notes = data["notes"]

    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_block_link(
    link_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    _ = user
    link = db.get(BlockLink, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Ligação não encontrada.")
    db.delete(link)
    db.commit()
