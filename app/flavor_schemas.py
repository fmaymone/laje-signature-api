"""Schemas do motor de composição por blocos de sabor."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas import CookingRequest, RecipeComponent


class SensoryProfile(BaseModel):
    acidity: float = Field(ge=0, le=10, default=0)
    saltiness: float = Field(ge=0, le=10, default=0)
    sweetness: float = Field(ge=0, le=10, default=0)
    bitterness: float = Field(ge=0, le=10, default=0)
    umami: float = Field(ge=0, le=10, default=0)
    fat: float = Field(ge=0, le=10, default=0)
    heat: float = Field(ge=0, le=10, default=0)
    aroma: float = Field(ge=0, le=10, default=0)
    freshness: float = Field(ge=0, le=10, default=0)


class TextureProfile(BaseModel):
    creamy: float = Field(ge=0, le=10, default=0)
    crunchy: float = Field(ge=0, le=10, default=0)
    crispy: float = Field(ge=0, le=10, default=0)
    juicy: float = Field(ge=0, le=10, default=0)
    firm: float = Field(ge=0, le=10, default=0)
    tender: float = Field(ge=0, le=10, default=0)
    chewy: float = Field(ge=0, le=10, default=0)


class IngredientUse(BaseModel):
    ingredient: str
    technique: str
    function: list[str]
    intensity: float = Field(ge=0, le=10, default=5)
    notes: str | None = None


class FlavorBlock(BaseModel):
    id: str
    name: str
    description: str

    regional_availability: float = Field(ge=0, le=10, default=8)

    ingredients: list[IngredientUse]

    sensory_profile: SensoryProfile
    texture_profile: TextureProfile = Field(default_factory=TextureProfile)

    compatible_protagonists: list[str] = Field(default_factory=list)
    compatible_blocks: list[str] = Field(default_factory=list)
    conflicting_blocks: list[str] = Field(default_factory=list)

    culinary_roles: list[str]
    # papéis: protagonist | base | sauce | acidity | texture | aroma
    forms: list[str] = Field(
        default_factory=list,
        description="Formas possíveis: molho, creme, crocante, emulsão, redução…",
    )
    seasonality: list[str] = Field(default_factory=list)


class FlavorFamily(BaseModel):
    id: str
    name: str
    core: list[str]
    supports: list[str] = Field(default_factory=list)
    acid_options: list[str] = Field(default_factory=list)
    sensory_direction: dict[str, str] = Field(default_factory=dict)
    preferred_block_ids: list[str] = Field(default_factory=list)


class NordesteIngredient(BaseModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    delicacy: float = Field(ge=0, le=10, default=5)
    regional_availability: float = Field(ge=0, le=10, default=8)
    sensory_profile: SensoryProfile = Field(default_factory=SensoryProfile)
    texture_profile: TextureProfile = Field(default_factory=TextureProfile)
    notes: str | None = None


class Substitution(BaseModel):
    from_ingredient: str
    to_ingredient: str
    reason: str
    confidence: float = Field(ge=0, le=1, default=0.8)


class SelectedBlock(BaseModel):
    block_id: str
    role: str
    chosen_form: str
    justification: str
    ingredients: list[IngredientUse] = Field(default_factory=list)


class DishArchitecture(BaseModel):
    """Arquitetura do prato antes da receita executável."""

    title: str
    concept: str
    protagonist: str
    family_id: str | None = None

    blocks: list[SelectedBlock]

    sensory_estimate: SensoryProfile
    texture_estimate: TextureProfile
    texture_contrast: float = Field(ge=0, le=10, default=0)

    balance_corrections: list[str] = Field(default_factory=list)
    composition_notes: list[str] = Field(default_factory=list)


class SensoryReport(BaseModel):
    sensory: SensoryProfile
    texture: TextureProfile
    texture_contrast: float
    corrections: list[str]
    multi_function_notes: list[str] = Field(default_factory=list)


class RegionalReport(BaseModel):
    allowed_ingredients: list[str]
    substitutions_applied: list[str]
    rejected: list[str]
    notes: list[str] = Field(default_factory=list)


class ExecutableRecipeDraft(BaseModel):
    """Saída do chef técnico a partir da arquitetura de blocos."""

    title: str
    concept: str
    components: list[RecipeComponent]
    plating: list[str]
    rationale: list[str]
    block_mapping: list[str] = Field(
        default_factory=list,
        description="Como cada componente mapeia para um bloco/função",
    )
