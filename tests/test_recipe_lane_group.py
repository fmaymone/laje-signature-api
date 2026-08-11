"""Testes de agrupamento de passos em lanes por process."""

from __future__ import annotations

from api.schemas_recipe_import import RecipeImageImportDraft
from api.schemas_recipes_persist import MAIN_LANE_ID, RecipeLane, RecipeStep
from app.recipe_lane_group import group_steps_into_lanes_by_process


def _step(sid: str, process: str, lane_id: str = MAIN_LANE_ID) -> RecipeStep:
    return RecipeStep(
        id=sid,
        process=process,
        description=f"desc {sid}",
        time_before_service_minutes=0,
        duration_minutes=10,
        lane_id=lane_id,
    )


def test_group_repeated_process_into_lane():
    draft = RecipeImageImportDraft(
        title="Feijoada",
        servings=4,
        ingredients=[],
        lanes=[RecipeLane(id=MAIN_LANE_ID, name="Principal")],
        steps=[
            _step("s1", "ensopado"),
            _step("s2", "ensopado"),
            _step("s3", "ensopado"),
            _step("s4", "servir"),
        ],
    )
    out = group_steps_into_lanes_by_process(draft)
    lane_ids = {lane.id for lane in out.lanes}
    assert MAIN_LANE_ID in lane_ids
    assert "ensopado" in lane_ids
    ensopado_steps = [s for s in out.steps if s.lane_id == "ensopado"]
    assert len(ensopado_steps) == 3
    assert all(s.process.lower() == "ensopado" for s in ensopado_steps)
    servir = next(s for s in out.steps if s.id == "s4")
    assert servir.lane_id == MAIN_LANE_ID
    ensopado_lane = next(lane for lane in out.lanes if lane.id == "ensopado")
    assert ensopado_lane.name == "Ensopado"


def test_no_group_when_all_processes_unique():
    draft = RecipeImageImportDraft(
        title="Simples",
        servings=2,
        ingredients=[],
        steps=[
            _step("s1", "refogar"),
            _step("s2", "temperar"),
            _step("s3", "servir"),
        ],
    )
    out = group_steps_into_lanes_by_process(draft)
    assert all(s.lane_id == MAIN_LANE_ID for s in out.steps)
    assert len(out.lanes) == 1


def test_case_insensitive_process_grouping():
    draft = RecipeImageImportDraft(
        title="Molho",
        servings=2,
        ingredients=[],
        steps=[
            _step("s1", "Ensopado"),
            _step("s2", "ENSOPADO"),
            _step("s3", "ensopado"),
        ],
    )
    out = group_steps_into_lanes_by_process(draft)
    assert all(s.lane_id == "ensopado" for s in out.steps)
