from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.deps import resolve_cooking_request, run_graph, stream_graph
from api.schemas import (
    ChatParseRequest,
    GenerateRecipeRequest,
    GenerateRecipeResponse,
)
from app.request_parser import parse_cooking_request
from app.schemas import CookingRequest

router = APIRouter(tags=["recipes"])


@router.post("/v1/chat/parse", response_model=CookingRequest)
def chat_parse(body: ChatParseRequest) -> CookingRequest:
    try:
        return parse_cooking_request(body.message)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/v1/recipes/generate", response_model=GenerateRecipeResponse)
def generate_recipe(body: GenerateRecipeRequest) -> GenerateRecipeResponse:
    try:
        request = resolve_cooking_request(
            message=body.message,
            request=body.request,
        )
        recipe, meta, request = run_graph(
            request,
            memories=body.memories,
            max_revisions=body.max_revisions,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return GenerateRecipeResponse(request=request, recipe=recipe, meta=meta)


@router.post("/v1/recipes/generate/stream")
def generate_recipe_stream(body: GenerateRecipeRequest) -> StreamingResponse:
    try:
        request = resolve_cooking_request(
            message=body.message,
            request=body.request,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    def event_generator():
        for event_type, payload in stream_graph(
            request,
            memories=body.memories,
            max_revisions=body.max_revisions,
        ):
            data = json.dumps(payload, ensure_ascii=False)
            yield f"event: {event_type}\ndata: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
