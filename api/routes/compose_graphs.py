"""CRUD do grafo de composição (canvas Compor)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.schemas_compose_graph import (
    CompositionGraphCreate,
    CompositionGraphListResponse,
    CompositionGraphRead,
    CompositionGraphUpdate,
)
from app.db.models import CompositionGraph
from app.db.session import get_db

router = APIRouter(prefix="/v1/compose/graphs", tags=["compose-graphs"])


def _dump_nodes(nodes) -> list[dict]:
    return [n.model_dump() for n in nodes]


def _dump_edges(edges) -> list[dict]:
    return [e.model_dump() for e in edges]


@router.post("", response_model=CompositionGraphRead, status_code=status.HTTP_201_CREATED)
def create_graph(
    payload: CompositionGraphCreate,
    db: Session = Depends(get_db),
) -> CompositionGraph:
    graph = CompositionGraph(
        title=payload.title.strip(),
        notes=payload.notes,
        nodes=_dump_nodes(payload.nodes),
        edges=_dump_edges(payload.edges),
    )
    db.add(graph)
    db.commit()
    db.refresh(graph)
    return graph


@router.get("", response_model=CompositionGraphListResponse)
def list_graphs(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> CompositionGraphListResponse:
    total = db.scalar(select(func.count()).select_from(CompositionGraph)) or 0
    items = db.scalars(
        select(CompositionGraph)
        .order_by(CompositionGraph.updated_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return CompositionGraphListResponse(items=list(items), total=total)


@router.get("/{graph_id}", response_model=CompositionGraphRead)
def get_graph(graph_id: uuid.UUID, db: Session = Depends(get_db)) -> CompositionGraph:
    graph = db.get(CompositionGraph, graph_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grafo não encontrado.")
    return graph


@router.put("/{graph_id}", response_model=CompositionGraphRead)
def update_graph(
    graph_id: uuid.UUID,
    payload: CompositionGraphUpdate,
    db: Session = Depends(get_db),
) -> CompositionGraph:
    graph = db.get(CompositionGraph, graph_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grafo não encontrado.")

    data = payload.model_dump(exclude_unset=True)
    if "title" in data and data["title"] is not None:
        graph.title = data["title"].strip()
    if "notes" in data:
        graph.notes = data["notes"]
    if "nodes" in data and data["nodes"] is not None:
        graph.nodes = data["nodes"]
    if "edges" in data and data["edges"] is not None:
        graph.edges = data["edges"]

    db.add(graph)
    db.commit()
    db.refresh(graph)
    return graph


@router.delete("/{graph_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_graph(graph_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    graph = db.get(CompositionGraph, graph_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grafo não encontrado.")
    db.delete(graph)
    db.commit()
