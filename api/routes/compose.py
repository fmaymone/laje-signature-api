from fastapi import APIRouter, HTTPException

from api.deps import preview_compose
from api.schemas import ComposePreviewResponse
from app.schemas import CookingRequest

router = APIRouter(prefix="/v1/compose", tags=["compose"])


@router.post("/preview", response_model=ComposePreviewResponse)
def compose_preview(request: CookingRequest) -> ComposePreviewResponse:
    try:
        payload = preview_compose(request)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ComposePreviewResponse(**payload)
