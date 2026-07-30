"""Schemas dos blocos de sabor editáveis."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SensoryProfileSchema(BaseModel):
    acidity: float = Field(ge=0, le=10, default=0)
    saltiness: float = Field(ge=0, le=10, default=0)
    sweetness: float = Field(ge=0, le=10, default=0)
    bitterness: float = Field(ge=0, le=10, default=0)
    umami: float = Field(ge=0, le=10, default=0)
    fat: float = Field(ge=0, le=10, default=0)
    heat: float = Field(ge=0, le=10, default=0)
    aroma: float = Field(ge=0, le=10, default=0)
    freshness: float = Field(ge=0, le=10, default=0)


class FlavorBlockWrite(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    family: str = Field(min_length=1, max_length=120)
    ingredient_ids: list[str] = Field(default_factory=list)
    culinary_roles: list[str] = Field(default_factory=list)
    compatible_protagonists: list[str] = Field(default_factory=list)
    recommended_base_ids: list[str] = Field(default_factory=list)
    target_sensory_profile: SensoryProfileSchema = Field(default_factory=SensoryProfileSchema)
    texture_targets: list[str] = Field(default_factory=list)
    techniques: list[str] = Field(default_factory=list)
    notes: str = ""


class FlavorBlockUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    family: str | None = Field(default=None, min_length=1, max_length=120)
    ingredient_ids: list[str] | None = None
    culinary_roles: list[str] | None = None
    compatible_protagonists: list[str] | None = None
    recommended_base_ids: list[str] | None = None
    target_sensory_profile: SensoryProfileSchema | None = None
    texture_targets: list[str] | None = None
    techniques: list[str] | None = None
    notes: str | None = None


class FlavorBlockRead(BaseModel):
    id: str
    name: str
    family: str
    ingredient_ids: list[str]
    culinary_roles: list[str]
    compatible_protagonists: list[str]
    recommended_base_ids: list[str]
    target_sensory_profile: SensoryProfileSchema
    texture_targets: list[str] = Field(default_factory=list)
    techniques: list[str] = Field(default_factory=list)
    notes: str = ""
    origin: Literal["catalog", "custom", "override"] = "catalog"
    editable: bool = False
    updated_at: datetime | str | None = None


class FlavorBlockListResponse(BaseModel):
    items: list[FlavorBlockRead]
    total: int
