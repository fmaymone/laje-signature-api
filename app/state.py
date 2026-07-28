from typing import TypedDict

from app.flavor_schemas import DishArchitecture, RegionalReport, SensoryReport
from app.schemas import (
    CookingRequest,
    FernandoReview,
    FinalRecipe,
    RecipeDraft,
    TechnicalReview,
)


class CulinaryState(TypedDict, total=False):
    request: CookingRequest

    chef_profile: str
    relevant_memories: list[str]
    relevant_recipes: list[str]

    regional_report: RegionalReport

    # Pipeline determinístico v0.1
    block_selection: dict
    catalog_result: dict
    compatibility_result: dict
    conflict_result: dict

    architecture: DishArchitecture
    sensory_report: SensoryReport

    draft: RecipeDraft
    technical_review: TechnicalReview
    fernando_review: FernandoReview

    final_recipe: FinalRecipe

    revision_count: int
    technical_revision_count: int
    max_revisions: int
