"""Carrega Biblioteca Fernando Nordeste v0.1.0."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import json
import sys

_LIBRARY_ROOT = (
    Path(__file__).resolve().parent.parent.parent / "data" / "library"
)


def library_root() -> Path:
    return _LIBRARY_ROOT


@lru_cache(maxsize=1)
def load_library() -> dict:
    """Usa loader.py da biblioteca ou library.json diretamente."""
    loader_path = _LIBRARY_ROOT / "loader.py"
    if loader_path.exists():
        if str(_LIBRARY_ROOT) not in sys.path:
            sys.path.insert(0, str(_LIBRARY_ROOT))
        from loader import load_library as _load  # type: ignore

        return _load(_LIBRARY_ROOT / "library.json")

    with (_LIBRARY_ROOT / "library.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def by_id(items: list[dict], key: str = "id") -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for item in items:
        item_id = item.get(key) or item.get("id") or item.get("ingredient_id")
        if item_id:
            indexed[item_id] = item
    return indexed


def reset_library_cache() -> None:
    load_library.cache_clear()


def index_library() -> dict[str, dict[str, dict]]:
    lib = load_library()
    return {
        "ingredients": by_id(lib["ingredients"]),
        "flavor_blocks": by_id(lib["flavor_blocks"]),
        "protagonists": by_id(lib["protagonists"]),
        "bases": by_id(lib["bases"]),
        "acidity_sources": by_id(lib["acidity_sources"]),
        "textures": by_id(lib["textures"]),
        "aromatic_families": by_id(lib["aromatic_families"]),
        "compatibility_rules": by_id(lib["compatibility_rules"]),
        "conflict_rules": by_id(lib["conflict_rules"]),
        "regional_substitutions": by_id(lib["regional_substitutions"]),
        "seasonality": by_id(lib["seasonality"], key="ingredient_id"),
    }
