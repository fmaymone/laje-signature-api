from pydantic import BaseModel, Field
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
    family: str
    ingredient_ids: list[str]
    culinary_roles: list[str]
    compatible_protagonists: list[str]
    recommended_base_ids: list[str]
    target_sensory_profile: SensoryProfile
    texture_targets: list[str]
    notes: str = ''
