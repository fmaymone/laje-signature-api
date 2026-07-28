"""Pacote de composição culinária determinística."""

from app.composition.blocks_composer import (
    apply_compatibility_rules,
    apply_conflict_rules,
    complete_from_catalogs,
    compose_from_library_v01,
    detect_protagonist_id,
    select_flavor_blocks,
    selection_to_architecture,
)
from app.composition.library_v01 import index_library, load_library, reset_library_cache

from app.composition.engine import (
    apply_regional_filter,
    compose_architecture,
    detect_protagonist,
    evaluate_balance,
    load_blocks,
    load_families,
    load_ingredients,
)

__all__ = [
    "apply_compatibility_rules",
    "apply_conflict_rules",
    "apply_regional_filter",
    "complete_from_catalogs",
    "compose_architecture",
    "compose_from_library_v01",
    "detect_protagonist",
    "detect_protagonist_id",
    "evaluate_balance",
    "index_library",
    "load_blocks",
    "load_families",
    "load_ingredients",
    "load_library",
    "reset_library_cache",
    "select_flavor_blocks",
    "selection_to_architecture",
]
