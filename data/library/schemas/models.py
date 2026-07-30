from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any


class SensoryProfile(BaseModel):
    acidity: float = Field(ge=0, le=10)
    saltiness: float = Field(ge=0, le=10)
    sweetness: float = Field(ge=0, le=10)
    bitterness: float = Field(ge=0, le=10)
    umami: float = Field(ge=0, le=10)
    fat: float = Field(ge=0, le=10)
    heat: float = Field(ge=0, le=10)
    aroma: float = Field(ge=0, le=10)
    freshness: float = Field(ge=0, le=10)


class Tag(BaseModel):
    id: str
    title: str


class Ingredient(BaseModel):
    id: str
    name: str
    aliases: list[str] = []
    category: str
    regional_status: str
    availability_zones: list[str]
    culinary_roles: list[str]
    sensory_profile: SensoryProfile
    recommended_techniques: list[str]
    seasonality_ref: str
    notes: Optional[str] = None


class FlavorBlock(BaseModel):
    id: str
    name: str
    family: Tag
    ingredient_ids: list[str]
    culinary_roles: list[str]
    compatible_protagonists: list[str]
    recommended_base_ids: list[str]
    target_sensory_profile: SensoryProfile
    texture_targets: list[str]
    techniques: list[Tag] = []
    notes: str = ''

    @field_validator('family', mode='before')
    @classmethod
    def _coerce_family(cls, value: Any) -> Any:
        from app.composition.tags import FAMILY_TITLES, coerce_tag

        tag = coerce_tag(value, catalog=FAMILY_TITLES)
        return tag.model_dump() if tag else value

    @field_validator('techniques', mode='before')
    @classmethod
    def _coerce_techniques(cls, value: Any) -> Any:
        from app.composition.tags import TECHNIQUE_TITLES, tags_as_dicts

        return tags_as_dicts(value, catalog=TECHNIQUE_TITLES)
