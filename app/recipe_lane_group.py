"""Agrupa passos repetidos por processo em lanes (linhas) da receita."""

from __future__ import annotations

from collections import defaultdict

from api.schemas_recipe_import import RecipeImageImportDraft
from api.schemas_recipes_persist import MAIN_LANE_ID, RecipeLane
from app.ingredient_resolve import slugify_ingredient


def _lane_id_for_process(process: str) -> str:
    slug = slugify_ingredient(process)
    if not slug or slug == MAIN_LANE_ID:
        return "lane_process"
    return slug[:120]


def _display_name(process: str) -> str:
    text = " ".join(process.strip().split())
    if not text:
        return "Linha"
    return text[0].upper() + text[1:]


def group_steps_into_lanes_by_process(draft: RecipeImageImportDraft) -> RecipeImageImportDraft:
    """Se o mesmo `process` aparece em 2+ passos, cria uma lane com esse nome.

    Passos únicos ficam em Principal (ou na lane que já tinham).
    """
    steps = list(draft.steps or [])
    if len(steps) < 2:
        return draft

    by_key: dict[str, list[int]] = defaultdict(list)
    for idx, step in enumerate(steps):
        by_key[_lane_id_for_process(step.process)].append(idx)

    multi_keys = {key for key, idxs in by_key.items() if len(idxs) >= 2}
    if not multi_keys:
        return draft

    lanes_by_id: dict[str, RecipeLane] = {
        MAIN_LANE_ID: RecipeLane(id=MAIN_LANE_ID, name="Principal"),
    }
    for lane in draft.lanes or []:
        if lane.id != MAIN_LANE_ID and lane.id not in multi_keys:
            lanes_by_id[lane.id] = lane

    new_steps = []
    for step in steps:
        key = _lane_id_for_process(step.process)
        if key in multi_keys:
            if key not in lanes_by_id:
                lanes_by_id[key] = RecipeLane(id=key, name=_display_name(step.process))
            new_steps.append(step.model_copy(update={"lane_id": key}))
        else:
            lane_id = step.lane_id or MAIN_LANE_ID
            if lane_id not in lanes_by_id:
                lanes_by_id[lane_id] = RecipeLane(
                    id=lane_id,
                    name="Principal" if lane_id == MAIN_LANE_ID else f"Linha {len(lanes_by_id)}",
                )
            new_steps.append(step.model_copy(update={"lane_id": lane_id}))

    ordered = [lanes_by_id[MAIN_LANE_ID]]
    # ordem: primeira aparição do process no fluxo
    seen_extra: set[str] = set()
    for step in new_steps:
        lid = step.lane_id
        if lid == MAIN_LANE_ID or lid in seen_extra:
            continue
        if lid in lanes_by_id:
            ordered.append(lanes_by_id[lid])
            seen_extra.add(lid)
    for lid, lane in lanes_by_id.items():
        if lid != MAIN_LANE_ID and lid not in seen_extra:
            ordered.append(lane)

    return draft.model_copy(update={"steps": new_steps, "lanes": ordered})
