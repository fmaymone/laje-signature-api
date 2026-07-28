from pydantic import BaseModel, Field


class CookingRequest(BaseModel):
    objective: str
    ingredients: list[str]
    servings: int = Field(ge=1, le=30)
    equipment: list[str]
    restrictions: list[str] = Field(default_factory=list)
    available_time_minutes: int | None = None


class RecipeComponent(BaseModel):
    name: str
    purpose: str
    ingredients: list[str]
    instructions: list[str]
    critical_points: list[str] = Field(default_factory=list)


class RecipeDraft(BaseModel):
    title: str
    concept: str
    components: list[RecipeComponent]
    plating: list[str]
    rationale: list[str]


class TechnicalReview(BaseModel):
    approved: bool
    problems: list[str]
    required_changes: list[str]
    timing_notes: list[str]
    safety_notes: list[str]


class FernandoReview(BaseModel):
    approved: bool
    score: float = Field(ge=0, le=10)
    feels_like_fernando: bool

    strengths: list[str]
    problems: list[str]
    required_changes: list[str]

    unnecessary_complexity: list[str]
    missing_contrasts: list[str]


class FinalRecipe(BaseModel):
    title: str
    concept: str
    servings: int

    components: list[RecipeComponent]
    equipment: list[str]
    mise_en_place: list[str]
    timeline: list[str]
    plating: list[str]

    critical_points: list[str]
    substitutions: list[str]
    conservation: list[str]

    why_this_matches_fernando: list[str]
    revision_warning: str | None = None
