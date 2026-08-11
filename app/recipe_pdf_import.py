"""Extrai receita de PDF: texto embutido ou render da página (scan)."""

from __future__ import annotations

import fitz  # pymupdf

from api.schemas_recipe_import import RecipeImageImportDraft
from app.recipe_document_parser import parse_recipe_from_document_text
from app.recipe_image_parser import parse_recipe_from_image

# Mínimo de caracteres "úteis" para preferir o caminho de texto
_MIN_TEXT_CHARS = 80
_MAX_TEXT_PAGES = 5
_MAX_RENDER_PAGES = 2


def _extract_text(doc: fitz.Document) -> str:
    parts: list[str] = []
    for i, page in enumerate(doc):
        if i >= _MAX_TEXT_PAGES:
            break
        parts.append(page.get_text("text") or "")
    return "\n".join(parts).strip()


def _render_pages_png(doc: fitz.Document) -> list[bytes]:
    """Renderiza até N páginas em PNG (para PDF escaneado)."""
    images: list[bytes] = []
    matrix = fitz.Matrix(2.0, 2.0)
    for i, page in enumerate(doc):
        if i >= _MAX_RENDER_PAGES:
            break
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        images.append(pix.tobytes("png"))
    return images


def parse_recipe_from_pdf(pdf_bytes: bytes) -> RecipeImageImportDraft:
    if not pdf_bytes:
        raise ValueError("PDF vazio.")
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"PDF inválido ou corrompido: {exc}") from exc

    try:
        if doc.page_count < 1:
            raise ValueError("PDF sem páginas.")

        text = _extract_text(doc)
        if len(text) >= _MIN_TEXT_CHARS:
            draft = parse_recipe_from_document_text(text)
            warnings = list(draft.warnings or [])
            if "PDF (texto)" not in " ".join(warnings):
                warnings.append("Importado de PDF (texto extraído).")
            return draft.model_copy(update={"warnings": warnings})

        # Scan / pouco texto: vision na(s) página(s)
        pngs = _render_pages_png(doc)
        if not pngs:
            raise ValueError("Não foi possível ler páginas do PDF.")

        draft = parse_recipe_from_image(image_bytes=pngs[0], mime_type="image/png")
        warnings = list(draft.warnings or [])
        warnings.append("Importado de PDF (página renderizada).")

        # Segunda página: funde ingredientes/passos se houver
        if len(pngs) > 1:
            try:
                extra = parse_recipe_from_image(image_bytes=pngs[1], mime_type="image/png")
                merged_ingredients = list(draft.ingredients) + list(extra.ingredients)
                merged_steps = list(draft.steps)
                for step in extra.steps:
                    sid = step.id
                    if any(s.id == sid for s in merged_steps):
                        step = step.model_copy(update={"id": f"{sid}_p2"})
                    merged_steps.append(step)
                notes = draft.notes
                if extra.notes:
                    notes = f"{notes}\n{extra.notes}".strip() if notes else extra.notes
                warnings.extend(extra.warnings or [])
                draft = draft.model_copy(
                    update={
                        "ingredients": merged_ingredients,
                        "steps": merged_steps,
                        "notes": notes,
                        "warnings": warnings,
                    }
                )
            except Exception:  # noqa: BLE001 — página extra é best-effort
                pass

        return draft.model_copy(update={"warnings": warnings})
    finally:
        doc.close()
