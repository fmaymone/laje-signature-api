"""Schemas de serviço (receitas + data/hora)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone

from pydantic import BaseModel, Field, field_validator


def _coerce_service_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, time(12, 0), tzinfo=timezone.utc)
    if isinstance(value, str):
        raw = value.strip()
        if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            d = date.fromisoformat(raw)
            return datetime.combine(d, time(12, 0), tzinfo=timezone.utc)
    return value  # type: ignore[return-value]


class ServiceCreate(BaseModel):
    name: str = Field(default="Serviço", min_length=1, max_length=200)
    notes: str | None = None
    service_date: datetime
    recipe_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)

    @field_validator("service_date", mode="before")
    @classmethod
    def coerce_service_date(cls, value: object) -> datetime | None:
        return _coerce_service_datetime(value)


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = None
    service_date: datetime | None = None
    recipe_ids: list[uuid.UUID] | None = Field(default=None, max_length=100)

    @field_validator("service_date", mode="before")
    @classmethod
    def coerce_service_date(cls, value: object) -> datetime | None:
        return _coerce_service_datetime(value)


class ServiceRead(BaseModel):
    id: uuid.UUID
    name: str
    notes: str | None = None
    owner_id: uuid.UUID | None = None
    service_date: datetime
    recipe_ids: list[uuid.UUID] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ServiceListResponse(BaseModel):
    items: list[ServiceRead]
    total: int
