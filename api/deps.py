"""Helpers compartilhados da API."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from app.composition import compose_from_library_v01
from app.graph import culinary_graph
from app.request_parser import parse_cooking_request
from app.schemas import CookingRequest, FinalRecipe
from api.schemas import RecipeMeta

STAGE_LABELS = {
    "retrieve": "contexto / RAG",
    "regional": "substituições regionais",
    "select_blocks": "blocos de sabor",
    "complete_catalogs": "bases / acidez / textura / aroma",
    "apply_compatibility": "regras de compatibilidade",
    "apply_conflicts": "regras de conflito",
    "write": "escrevendo receita",
    "technical": "revisão técnica",
    "critic": "crítico Fernando",
    "finalizer": "finalizando",
}

LIBRARY_COLLECTIONS = (
    "ingredients",
    "flavor_blocks",
    "protagonists",
    "bases",
    "acidity_sources",
    "textures",
    "aromatic_families",
    "compatibility_rules",
    "conflict_rules",
    "regional_substitutions",
    "seasonality",
)


def ensure_equipment(request: CookingRequest) -> CookingRequest:
    if request.equipment:
        return request
    return request.model_copy(
        update={"equipment": ["Thermomix TM7", "churrasqueira"]}
    )


def resolve_cooking_request(
    *,
    message: str | None,
    request: CookingRequest | None,
) -> CookingRequest:
    if request is not None:
        return ensure_equipment(request)
    if message and message.strip():
        return ensure_equipment(parse_cooking_request(message.strip()))
    raise ValueError("Informe 'message' ou 'request'.")


def meta_from_state(state: dict) -> RecipeMeta:
    blocks_state = state.get("conflict_result") or state.get("block_selection") or {}
    block_ids = [
        block.get("id")
        for block in blocks_state.get("selected_blocks", [])
        if isinstance(block, dict)
    ]
    review = state.get("fernando_review")
    return RecipeMeta(
        blocks=block_ids,
        catalog_picks=blocks_state.get("catalog_picks", []) or [],
        seasonality_notes=(blocks_state.get("seasonality_notes", []) or [])[:8],
        score=getattr(review, "score", None),
        approved=getattr(review, "approved", None),
        revisions=int(state.get("revision_count", 0) or 0),
    )


def run_graph(
    request: CookingRequest,
    memories: list[str],
    max_revisions: int = 1,
) -> tuple[FinalRecipe, RecipeMeta, CookingRequest]:
    request = ensure_equipment(request)
    payload = {
        "request": request,
        "relevant_memories": list(memories),
        "revision_count": 0,
        "max_revisions": max_revisions,
    }
    state: dict[str, Any] = dict(payload)
    for event in culinary_graph.stream(payload, stream_mode="updates"):
        for _node_name, update in event.items():
            if isinstance(update, dict):
                state.update(update)
    return state["final_recipe"], meta_from_state(state), request


def stream_graph(
    request: CookingRequest,
    memories: list[str],
    max_revisions: int = 1,
) -> Iterator[tuple[str, dict]]:
    """Yields ('stage', {...}) and finally ('result', {...}) or ('error', {...})."""
    request = ensure_equipment(request)
    payload = {
        "request": request,
        "relevant_memories": list(memories),
        "revision_count": 0,
        "max_revisions": max_revisions,
    }
    state: dict[str, Any] = dict(payload)
    try:
        for event in culinary_graph.stream(payload, stream_mode="updates"):
            for node_name, update in event.items():
                if isinstance(update, dict):
                    state.update(update)
                yield (
                    "stage",
                    {
                        "node": node_name,
                        "label": STAGE_LABELS.get(node_name, node_name),
                    },
                )
        recipe = state["final_recipe"]
        meta = meta_from_state(state)
        yield (
            "result",
            {
                "request": request.model_dump(),
                "recipe": recipe.model_dump(),
                "meta": meta.model_dump(),
            },
        )
    except Exception as exc:  # noqa: BLE001
        yield ("error", {"message": str(exc)})


def preview_compose(request: CookingRequest) -> dict:
    request = ensure_equipment(request)
    mentions = list(request.ingredients) + [request.objective, *request.equipment]
    resolved, architecture = compose_from_library_v01(
        mentions=mentions,
        equipment=request.equipment,
    )
    return {
        "protagonist_id": resolved.get("protagonist_id") or architecture.protagonist,
        "blocks": resolved.get("selected_blocks", []),
        "covered_roles": resolved.get("covered_roles", []),
        "catalog_picks": resolved.get("catalog_picks", []),
        "seasonality_notes": resolved.get("seasonality_notes", []),
        "sensory": resolved.get("sensory", {}),
        "texture_targets": resolved.get("texture_targets", []),
        "architecture": architecture.model_dump(),
        "compatibility_triggered": resolved.get("compatibility_triggered", []),
        "conflicts_triggered": resolved.get("conflicts_triggered", []),
    }
