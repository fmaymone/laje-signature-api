"""Schemas dos blocos de sabor editáveis."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.composition.tags import FAMILY_TITLES, TECHNIQUE_TITLES, coerce_tag, tags_as_dicts


class TagSchema(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)


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


def _parse_family(value: Any) -> TagSchema:
    tag = coerce_tag(value, catalog=FAMILY_TITLES)
    if tag is None:
        raise ValueError("Família inválida")
    return TagSchema.model_validate(tag.model_dump())


def _parse_techniques(value: Any) -> list[TagSchema]:
    return [TagSchema.model_validate(item) for item in tags_as_dicts(value, catalog=TECHNIQUE_TITLES)]


class FlavorBlockWrite(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    family: TagSchema
    ingredient_ids: list[str] = Field(default_factory=list)
    culinary_roles: list[str] = Field(default_factory=list)
    compatible_protagonists: list[str] = Field(default_factory=list)
    recommended_base_ids: list[str] = Field(default_factory=list)
    target_sensory_profile: SensoryProfileSchema = Field(default_factory=SensoryProfileSchema)
    texture_targets: list[str] = Field(default_factory=list)
    techniques: list[TagSchema] = Field(default_factory=list)
    notes: str = ""

    @field_validator("family", mode="before")
    @classmethod
    def _family(cls, value: Any) -> TagSchema:
        return _parse_family(value)

    @field_validator("techniques", mode="before")
    @classmethod
    def _techniques(cls, value: Any) -> list[TagSchema]:
        return _parse_techniques(value)


class FlavorBlockUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    family: TagSchema | None = None
    ingredient_ids: list[str] | None = None
    culinary_roles: list[str] | None = None
    compatible_protagonists: list[str] | None = None
    recommended_base_ids: list[str] | None = None
    target_sensory_profile: SensoryProfileSchema | None = None
    texture_targets: list[str] | None = None
    techniques: list[TagSchema] | None = None
    notes: str | None = None

    @field_validator("family", mode="before")
    @classmethod
    def _family(cls, value: Any) -> TagSchema | None:
        if value is None:
            return None
        return _parse_family(value)

    @field_validator("techniques", mode="before")
    @classmethod
    def _techniques(cls, value: Any) -> list[TagSchema] | None:
        if value is None:
            return None
        return _parse_techniques(value)


class FlavorBlockRead(BaseModel):
    id: str
    name: str
    family: TagSchema
    ingredient_ids: list[str]
    culinary_roles: list[str]
    compatible_protagonists: list[str]
    recommended_base_ids: list[str]
    target_sensory_profile: SensoryProfileSchema
    texture_targets: list[str] = Field(default_factory=list)
    techniques: list[TagSchema] = Field(default_factory=list)
    notes: str = ""
    origin: Literal["catalog", "custom", "override"] = "catalog"
    editable: bool = False
    updated_at: datetime | str | None = None

    @field_validator("family", mode="before")
    @classmethod
    def _family(cls, value: Any) -> TagSchema:
        return _parse_family(value)

    @field_validator("techniques", mode="before")
    @classmethod
    def _techniques(cls, value: Any) -> list[TagSchema]:
        return _parse_techniques(value)


class FlavorBlockListResponse(BaseModel):
    items: list[FlavorBlockRead]
    total: int
