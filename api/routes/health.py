from fastapi import APIRouter

from api.schemas import HealthResponse
from app.composition.library_v01 import load_library
from app.db.session import check_db_connection

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    lib = load_library()
    metadata = lib.get("metadata") or {}
    version = (
        metadata.get("version")
        or metadata.get("library_version")
        or "0.1.0"
    )
    try:
        check_db_connection()
        db_status = "ok"
    except Exception:
        db_status = "error"

    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        library_version=str(version),
        database=db_status,
    )
