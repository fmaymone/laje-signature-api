"""Schemas de serviço (receitas + data)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class ServiceCreate(BaseModel):
    name: str = Field(default="Serviço", min_length=1, max_length=200)
    notes: str | None = None
    service_date: date
    recipe_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = None
    service_date: date | None = None
    recipe_ids: list[uuid.UUID] | None = Field(default=None, max_length=100)


class ServiceRead(BaseModel):
    id: uuid.UUID
    name: str
    notes: str | None = None
    owner_id: uuid.UUID | None = None
    service_date: date
    recipe_ids: list[uuid.UUID] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ServiceListResponse(BaseModel):
    items: list[ServiceRead]
    total: int
