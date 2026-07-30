"""CRUD de blocos de sabor (catálogo + persistência)."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from api.routes.auth import get_current_user
from api.schemas_blocks import (
    FlavorBlockListResponse,
    FlavorBlockRead,
    FlavorBlockUpdate,
    FlavorBlockWrite,
)
from app.composition.blocks_store import get_merged_flavor_block, merge_flavor_blocks
from app.composition.library_v01 import load_library
from app.composition.tags import tag_id
from app.db.models import FlavorBlockRecord, User
from app.db.session import get_db

router = APIRouter(prefix="/v1/blocks", tags=["blocks"])


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
    return text.strip("_")[:120] or "bloco"


def _payload_from_write(data: FlavorBlockWrite) -> dict:
    payload = data.model_dump()
    payload["id"] = _slugify(payload["id"])
    return payload


def _to_read(item: dict) -> FlavorBlockRead:
    return FlavorBlockRead.model_validate(item)


@router.get("", response_model=FlavorBlockListResponse)
@router.get("/", response_model=FlavorBlockListResponse, include_in_schema=False)
def list_blocks(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None),
    family: str | None = Query(default=None),
    origin: str | None = Query(default=None, description="catalog|custom|override"),
) -> FlavorBlockListResponse:
    items = merge_flavor_blocks(db)
    if family:
        family_needle = tag_id(family) or family.strip().lower()
        items = [item for item in items if tag_id(item.get("family")) == family_needle]
    if origin:
        items = [item for item in items if item.get("origin") == origin]
    if q:
        needle = q.lower().strip()

        def _matches(item: dict) -> bool:
            family_value = item.get("family") or {}
            family_blob = (
                f"{family_value.get('id', '')} {family_value.get('title', '')}"
                if isinstance(family_value, dict)
                else str(family_value)
            )
            techniques = item.get("techniques") or []
            tech_blob = " ".join(
                f"{t.get('id', '')} {t.get('title', '')}" if isinstance(t, dict) else str(t)
                for t in techniques
            )
            return (
                needle in str(item.get("id", "")).lower()
                or needle in str(item.get("name", "")).lower()
                or needle in family_blob.lower()
                or needle in tech_blob.lower()
                or any(needle in str(role).lower() for role in item.get("culinary_roles") or [])
            )

        items = [item for item in items if _matches(item)]
    return FlavorBlockListResponse(items=[_to_read(item) for item in items], total=len(items))


@router.get("/{block_id}", response_model=FlavorBlockRead)
def get_block(block_id: str, db: Session = Depends(get_db)) -> FlavorBlockRead:
    item = get_merged_flavor_block(block_id, db)
    if not item:
        raise HTTPException(status_code=404, detail="Bloco não encontrado.")
    return _to_read(item)


@router.post("", response_model=FlavorBlockRead, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=FlavorBlockRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_block(
    payload: FlavorBlockWrite,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FlavorBlockRead:
    data = _payload_from_write(payload)
    block_id = data["id"]
    if not block_id:
        raise HTTPException(status_code=400, detail="Informe um id válido.")

    existing = get_merged_flavor_block(block_id, db)
    if existing:
        raise HTTPException(status_code=409, detail="Já existe um bloco com este id.")

    row = FlavorBlockRecord(
        id=block_id,
        name=data["name"].strip(),
        is_custom=True,
        payload=data,
        notes=data.get("notes") or None,
        created_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_read(get_merged_flavor_block(block_id, db) or data)


@router.put("/{block_id}", response_model=FlavorBlockRead)
def update_block(
    block_id: str,
    payload: FlavorBlockUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FlavorBlockRead:
    current = get_merged_flavor_block(block_id, db)
    if not current:
        raise HTTPException(status_code=404, detail="Bloco não encontrado.")

    patch = payload.model_dump(exclude_unset=True)
    merged = {**current, **patch}
    if "target_sensory_profile" in patch and patch["target_sensory_profile"] is not None:
        merged["target_sensory_profile"] = patch["target_sensory_profile"]
    merged["id"] = block_id
    merged.pop("origin", None)
    merged.pop("editable", None)
    merged.pop("updated_at", None)

    catalog_ids = {b["id"] for b in load_library().get("flavor_blocks") or []}
    row = db.get(FlavorBlockRecord, block_id)
    if row is None:
        row = FlavorBlockRecord(
            id=block_id,
            name=str(merged.get("name") or block_id),
            is_custom=block_id not in catalog_ids,
            payload=merged,
            notes=merged.get("notes") or None,
            created_by=user.id,
        )
        db.add(row)
    else:
        row.name = str(merged.get("name") or block_id)
        row.payload = merged
        row.notes = merged.get("notes") or None
        flag_modified(row, "payload")
        db.add(row)

    db.commit()
    db.refresh(row)
    return _to_read(get_merged_flavor_block(block_id, db) or merged)


@router.delete("/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_block(
    block_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    _ = user
    row = db.get(FlavorBlockRecord, block_id)
    if row is not None:
        db.delete(row)
        db.commit()
        return

    catalog_ids = {b["id"] for b in load_library().get("flavor_blocks") or []}
    if block_id in catalog_ids:
        raise HTTPException(
            status_code=400,
            detail="Blocos do catálogo base não podem ser excluídos. Edite para criar um override, ou ignore-o.",
        )
    raise HTTPException(status_code=404, detail="Bloco não encontrado.")
