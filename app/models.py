from pydantic import BaseModel, Field


class Ingredient(BaseModel):
    name: str
    quantity_g: float | None = None
    preparation: str | None = None


class Component(BaseModel):
    name: str
    ingredients: list[Ingredient]
    instructions: list[str]
    critical_points: list[str] = Field(default_factory=list)


class CulinaryPlan(BaseModel):
    title: str
    concept: str
    servings: int
    total_time_minutes: int
    components: list[Component]
    equipment: list[str]
    timeline: list[str]
    plating: list[str]
    substitutions: list[str] = Field(default_factory=list)
    chef_reasoning_summary: list[str]
