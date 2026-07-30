"""CRUD do grafo de composição (canvas Composições)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.routes.auth import get_current_user
from api.schemas_compose_graph import (
    CompositionGraphCreate,
    CompositionGraphListResponse,
    CompositionGraphRead,
    CompositionGraphUpdate,
)
from app.db.models import CompositionGraph, User
from app.db.session import get_db

router = APIRouter(prefix="/v1/compose/graphs", tags=["compose-graphs"])


def _dump_nodes(nodes) -> list[dict]:
    return [n.model_dump() for n in nodes]


def _dump_edges(edges) -> list[dict]:
    return [e.model_dump() for e in edges]


def _get_owned_graph(
    db: Session,
    graph_id: uuid.UUID,
    user: User,
) -> CompositionGraph:
    graph = db.get(CompositionGraph, graph_id)
    if not graph or graph.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Composição não encontrada.")
    return graph


@router.post("", response_model=CompositionGraphRead, status_code=status.HTTP_201_CREATED)
def create_graph(
    payload: CompositionGraphCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CompositionGraph:
    graph = CompositionGraph(
        title=payload.title.strip() or "Composição",
        notes=payload.notes,
        owner_id=user.id,
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
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> CompositionGraphListResponse:
    owned = CompositionGraph.owner_id == user.id
    total = db.scalar(select(func.count()).select_from(CompositionGraph).where(owned)) or 0
    items = db.scalars(
        select(CompositionGraph)
        .where(owned)
        .order_by(CompositionGraph.updated_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return CompositionGraphListResponse(items=list(items), total=total)


@router.get("/{graph_id}", response_model=CompositionGraphRead)
def get_graph(
    graph_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CompositionGraph:
    return _get_owned_graph(db, graph_id, user)


@router.put("/{graph_id}", response_model=CompositionGraphRead)
def update_graph(
    graph_id: uuid.UUID,
    payload: CompositionGraphUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CompositionGraph:
    graph = _get_owned_graph(db, graph_id, user)

    data = payload.model_dump(exclude_unset=True)
    if "title" in data and data["title"] is not None:
        graph.title = data["title"].strip() or graph.title
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
def delete_graph(
    graph_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    graph = _get_owned_graph(db, graph_id, user)
    db.delete(graph)
    db.commit()
