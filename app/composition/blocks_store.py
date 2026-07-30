"""Merge catálogo YAML + registros persistidos de blocos."""

from __future__ import annotations

from copy import deepcopy
import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.composition.library_v01 import load_library
from app.db.models.flavor_block_record import FlavorBlockRecord
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def _annotate_catalog(block: dict) -> dict:
    item = deepcopy(block)
    item["origin"] = "catalog"
    item["editable"] = True  # pode gerar override
    item["updated_at"] = None
    return item


def _from_record(row: FlavorBlockRecord) -> dict:
    payload = deepcopy(row.payload) if isinstance(row.payload, dict) else {}
    payload["id"] = row.id
    payload["name"] = row.name or payload.get("name") or row.id
    payload["origin"] = "custom" if row.is_custom else "override"
    payload["editable"] = True
    payload["updated_at"] = row.updated_at.isoformat() if row.updated_at else None
    if "notes" not in payload:
        payload["notes"] = row.notes or ""
    return payload


def _load_records(session: Session) -> list[FlavorBlockRecord]:
    try:
        return list(session.scalars(select(FlavorBlockRecord)).all())
    except SQLAlchemyError as exc:
        logger.debug("flavor_block_records unavailable, using catalog only: %s", exc)
        return []


def merge_flavor_blocks(db: Session | None = None) -> list[dict]:
    catalog = list(load_library().get("flavor_blocks") or [])
    merged = {_annotate_catalog(block)["id"]: _annotate_catalog(block) for block in catalog}

    owns_session = db is None
    session = db or SessionLocal()
    try:
        for row in _load_records(session):
            merged[row.id] = _from_record(row)
    finally:
        if owns_session:
            session.close()

    return sorted(merged.values(), key=lambda item: str(item.get("name", item["id"])).lower())


def get_merged_flavor_block(block_id: str, db: Session | None = None) -> dict | None:
    for block in merge_flavor_blocks(db):
        if block.get("id") == block_id:
            return block
    return None
