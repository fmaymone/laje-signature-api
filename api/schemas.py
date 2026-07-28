"""API schemas (request/response)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas import CookingRequest, FinalRecipe


class HealthResponse(BaseModel):
    status: str
    library_version: str


class LibrarySummary(BaseModel):
    version: str
    counts: dict[str, int]


class ChatParseRequest(BaseModel):
    message: str = Field(min_length=1)


class GenerateRecipeRequest(BaseModel):
    message: str | None = None
    request: CookingRequest | None = None
    memories: list[str] = Field(default_factory=list)
    max_revisions: int = Field(default=1, ge=0, le=3)


class RecipeMeta(BaseModel):
    blocks: list[str] = Field(default_factory=list)
    catalog_picks: list[dict] = Field(default_factory=list)
    seasonality_notes: list[str] = Field(default_factory=list)
    score: float | None = None
    approved: bool | None = None
    revisions: int = 0


class GenerateRecipeResponse(BaseModel):
    request: CookingRequest
    recipe: FinalRecipe
    meta: RecipeMeta


class ComposePreviewResponse(BaseModel):
    protagonist_id: str
    blocks: list[dict]
    covered_roles: list[str]
    catalog_picks: list[dict] = Field(default_factory=list)
    seasonality_notes: list[str] = Field(default_factory=list)
    sensory: dict
    texture_targets: list[str] = Field(default_factory=list)
    architecture: dict
    compatibility_triggered: list[dict] = Field(default_factory=list)
    conflicts_triggered: list[dict] = Field(default_factory=list)
