from fastapi import APIRouter

from api.schemas import HealthResponse
from app.composition.library_v01 import load_library

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
    return HealthResponse(status="ok", library_version=str(version))
