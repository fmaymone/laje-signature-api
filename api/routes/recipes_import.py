"""Importação de receita a partir de print/imagem (vision → draft)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from api.routes.auth import get_current_user
from api.schemas_recipe_import import RecipeImageImportResponse
from app.ingredient_resolve import resolve_draft_ingredients
from app.recipe_image_parser import parse_recipe_from_image
from app.db.models import User
from app.db.session import get_db

router = APIRouter(prefix="/v1/recipes", tags=["recipe-import"])

ALLOWED_MIME = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
MAX_BYTES = 8 * 1024 * 1024  # 8 MB


def _normalize_mime(content_type: str | None, filename: str | None) -> str:
    mime = (content_type or "").split(";")[0].strip().lower()
    if mime in ALLOWED_MIME:
        return "image/jpeg" if mime == "image/jpg" else mime
    # fallback by extension when client omits/mistypes content-type
    name = (filename or "").lower()
    if name.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if name.endswith(".png"):
        return "image/png"
    if name.endswith(".webp"):
        return "image/webp"
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Envie uma imagem JPEG, PNG ou WebP.",
    )


@router.post(
    "/import-from-image",
    response_model=RecipeImageImportResponse,
    status_code=status.HTTP_200_OK,
)
async def import_recipe_from_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RecipeImageImportResponse:
    mime = _normalize_mime(file.content_type, file.filename)
    raw = await file.read()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de imagem vazio.",
        )
    if len(raw) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Imagem maior que 8 MB.",
        )

    try:
        draft = parse_recipe_from_image(image_bytes=raw, mime_type=mime)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001 — falha do provider/vision
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao ler a imagem com a AI: {exc}",
        ) from exc

    ingredients, created_names = resolve_draft_ingredients(db, draft=draft, user=user)

    return RecipeImageImportResponse(
        title=draft.title,
        notes=draft.notes,
        composition_id=None,
        servings=draft.servings,
        block_ids=[],
        ingredients=ingredients,
        lanes=draft.lanes,
        steps=draft.steps,
        created_ingredient_names=created_names,
        warnings=list(draft.warnings or []),
    )
