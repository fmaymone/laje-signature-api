"""Schemas do grafo de composição (canvas Compor)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


HandleSide = Literal["top", "right", "bottom", "left"]
LinkWeight = Literal[1, 2, 3]


class GraphNodePosition(BaseModel):
    x: float
    y: float


class GraphNode(BaseModel):
    id: str = Field(min_length=1)
    block_id: str = Field(min_length=1)
    position: GraphNodePosition


class GraphEdge(BaseModel):
    id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    sourceHandle: HandleSide | None = None
    targetHandle: HandleSide | None = None
    weight: LinkWeight = 2


class CompositionGraphCreate(BaseModel):
    title: str = Field(default="Composição", min_length=1, max_length=200)
    notes: str | None = None
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class CompositionGraphUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = None
    nodes: list[GraphNode] | None = None
    edges: list[GraphEdge] | None = None


class CompositionGraphRead(BaseModel):
    id: uuid.UUID
    title: str
    notes: str | None = None
    owner_id: uuid.UUID | None = None
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompositionGraphListResponse(BaseModel):
    items: list[CompositionGraphRead]
    total: int
