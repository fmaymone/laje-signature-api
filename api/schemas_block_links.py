"""Schemas de ligação ponderada entre blocos."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


LinkWeight = Literal[1, 2, 3]


class BlockLinkCreate(BaseModel):
    source_block_id: str = Field(min_length=1, max_length=120)
    target_block_id: str = Field(min_length=1, max_length=120)
    weight: LinkWeight = 2
    notes: str | None = None

    @model_validator(mode="after")
    def different_blocks(self) -> BlockLinkCreate:
        if self.source_block_id == self.target_block_id:
            raise ValueError("source_block_id e target_block_id devem ser diferentes.")
        return self


class BlockLinkUpdate(BaseModel):
    weight: LinkWeight | None = None
    notes: str | None = None


class BlockLinkRead(BaseModel):
    id: uuid.UUID
    source_block_id: str
    target_block_id: str
    weight: LinkWeight
    notes: str | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BlockLinkListResponse(BaseModel):
    items: list[BlockLinkRead]
    total: int


class BlockLinkBulkItem(BaseModel):
    target_block_id: str = Field(min_length=1, max_length=120)
    weight: LinkWeight = 2
    notes: str | None = None


class BlockLinkBulkCreate(BaseModel):
    source_block_id: str = Field(min_length=1, max_length=120)
    links: list[BlockLinkBulkItem] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def no_self_links(self) -> BlockLinkBulkCreate:
        source = self.source_block_id.strip()
        for item in self.links:
            if item.target_block_id.strip() == source:
                raise ValueError("Não é possível ligar um bloco a si mesmo.")
        return self


class BlockLinkBulkResult(BaseModel):
    created: int
    updated: int
    skipped: int
    items: list[BlockLinkRead]
