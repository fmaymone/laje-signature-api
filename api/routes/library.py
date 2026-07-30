from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.deps import LIBRARY_COLLECTIONS
from api.schemas import LibrarySummary
from app.composition.blocks_store import get_merged_flavor_block, merge_flavor_blocks
from app.composition.library_v01 import index_library, load_library
from app.db.session import get_db

router = APIRouter(prefix="/v1/library", tags=["library"])


def _item_id(item: dict, collection: str) -> str | None:
    if collection == "seasonality":
        return item.get("ingredient_id") or item.get("id")
    return item.get("id") or item.get("ingredient_id")


def _matches_query(item: dict, q: str) -> bool:
    needle = q.lower().strip()
    if not needle:
        return True
    haystacks = [
        str(item.get("id", "")),
        str(item.get("name", "")),
        str(item.get("ingredient_id", "")),
        str(item.get("original", "")),
        " ".join(item.get("aliases", []) or []),
    ]
    return any(needle in value.lower() for value in haystacks if value)


@router.get("/summary", response_model=LibrarySummary)
def library_summary(db: Session = Depends(get_db)) -> LibrarySummary:
    lib = load_library()
    metadata = lib.get("metadata") or {}
    version = str(
        metadata.get("version")
        or metadata.get("library_version")
        or "0.2.0"
    )
    counts = {
        key: len(lib[key])
        for key in LIBRARY_COLLECTIONS
        if isinstance(lib.get(key), list)
    }
    counts["flavor_blocks"] = len(merge_flavor_blocks(db))
    return LibrarySummary(version=version, counts=counts)


@router.get("/{collection}")
def list_collection(
    collection: str,
    q: str | None = Query(default=None, description="Filtro por id/nome"),
    db: Session = Depends(get_db),
) -> list[dict]:
    if collection not in LIBRARY_COLLECTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Coleção inválida. Use: {', '.join(LIBRARY_COLLECTIONS)}",
        )
    if collection == "flavor_blocks":
        items = merge_flavor_blocks(db)
    else:
        lib = load_library()
        items = list(lib.get(collection) or [])
    if q:
        items = [item for item in items if _matches_query(item, q)]
    return items


@router.get("/{collection}/{item_id}")
def get_collection_item(
    collection: str,
    item_id: str,
    db: Session = Depends(get_db),
) -> dict:
    if collection not in LIBRARY_COLLECTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Coleção inválida. Use: {', '.join(LIBRARY_COLLECTIONS)}",
        )
    if collection == "flavor_blocks":
        item = get_merged_flavor_block(item_id, db)
        if item is None:
            raise HTTPException(status_code=404, detail="Item não encontrado")
        return item

    indexed = index_library().get(collection, {})
    item = indexed.get(item_id)
    if item is None:
        lib = load_library()
        for candidate in lib.get(collection) or []:
            if _item_id(candidate, collection) == item_id:
                return candidate
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return item
