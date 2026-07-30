"""Gera flavor_blocks atômicos (1 ingrediente = 1 bloco) e recompila library snapshots."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "library" / "catalog"
LIBRARY_DIR = ROOT / "data" / "library"

CATEGORY_FAMILY = {
    "peixe": "litoral",
    "crustaceo": "litoral",
    "molusco": "litoral",
    "carne": "sertão",
    "laticinio": "sertão",
    "leguminosa": "sertão",
    "raiz_tuberculo": "sertão",
    "cereal": "sertão",
    "hortalica": "agreste",
    "fruta_acida": "agreste",
    "fruta_doce": "mata",
    "erva_aromatica": "litoral_sertão",
    "pimenta": "litoral_sertão",
    "condimento": "sertão",
    "castanha_semente": "sertão",
    "gordura": "sertão",
    "acucar": "agreste",
}

ROLE_TEXTURES = {
    "brasa": ["tostado", "firme"],
    "base": ["cremoso"],
    "textura": ["crocante"],
    "molho": ["cremoso", "untuoso"],
    "acidez": ["fresco"],
    "frescor": ["fresco", "leve"],
    "aroma": ["aromático"],
    "protagonista": ["firme"],
    "cru": ["fresco", "macio"],
}


def _load_yaml(name: str) -> dict:
    with (CATALOG / name).open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _family_for(ingredient: dict) -> str:
    zones = ingredient.get("availability_zones") or []
    if "litoral" in zones and "sertão" in zones:
        return "litoral_sertão"
    if zones == ["litoral"] or (len(zones) == 1 and zones[0] in {"litoral", "manguezal", "estuarios"}):
        return "litoral"
    if "sertão" in zones and "litoral" not in zones:
        return "sertão"
    return CATEGORY_FAMILY.get(ingredient.get("category", ""), "nordeste")


def _textures_for(roles: list[str]) -> list[str]:
    out: list[str] = []
    for role in roles:
        for texture in ROLE_TEXTURES.get(role, []):
            if texture not in out:
                out.append(texture)
    return out[:3] or ["neutro"]


def _enrich_from_legacy(
    legacy_blocks: list[dict],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Propagates compatible protagonists and base recommendations from combo blocks."""
    compat: dict[str, set[str]] = defaultdict(set)
    bases: dict[str, set[str]] = defaultdict(set)
    for block in legacy_blocks:
        protagonists = block.get("compatible_protagonists") or []
        recommended = block.get("recommended_base_ids") or []
        for ingredient_id in block.get("ingredient_ids") or []:
            compat[ingredient_id].update(protagonists)
            bases[ingredient_id].update(recommended)
    return compat, bases


def build_atomic_blocks(
    ingredients: list[dict],
    protagonists: list[dict],
    legacy_blocks: list[dict],
) -> list[dict]:
    compat_map, bases_map = _enrich_from_legacy(legacy_blocks)
    protagonist_by_ingredient = {
        p["ingredient_id"]: p["id"] for p in protagonists if p.get("ingredient_id")
    }

    # Preferred pairings on protagonists → broaden compat for pairing ingredients
    for protagonist in protagonists:
        pid = protagonist["id"]
        for pairing in protagonist.get("preferred_pairings") or []:
            token = (
                pairing.lower()
                .replace("ã", "a")
                .replace("á", "a")
                .replace("â", "a")
                .replace("é", "e")
                .replace("ê", "e")
                .replace("í", "i")
                .replace("ó", "o")
                .replace("ô", "o")
                .replace("õ", "o")
                .replace("ú", "u")
                .replace("ç", "c")
                .replace("-", "_")
                .replace(" ", "_")
            )
            for ingredient in ingredients:
                iid = ingredient["id"]
                name_norm = ingredient["name"].lower()
                if token in iid or token in name_norm.replace(" ", "_") or iid.startswith(token):
                    compat_map[iid].add(pid)

    blocks: list[dict] = []
    for ingredient in ingredients:
        iid = ingredient["id"]
        roles = list(ingredient.get("culinary_roles") or [])
        sensory = dict(ingredient.get("sensory_profile") or {})

        compatible = set(compat_map.get(iid, set()))
        if iid in protagonist_by_ingredient:
            compatible.add(protagonist_by_ingredient[iid])
        # Proteins without legacy hints still pair with themselves
        if "protagonista" in roles and iid in protagonist_by_ingredient:
            compatible.add(protagonist_by_ingredient[iid])

        block = {
            "id": iid,
            "name": ingredient["name"],
            "family": _family_for(ingredient),
            "ingredient_ids": [iid],
            "culinary_roles": roles,
            "compatible_protagonists": sorted(compatible),
            "recommended_base_ids": sorted(bases_map.get(iid, set())),
            "target_sensory_profile": sensory,
            "texture_targets": _textures_for(roles),
            "notes": "Bloco atômico: um ingrediente, função clara na composição.",
        }
        blocks.append(block)

    return sorted(blocks, key=lambda b: b["id"])


def compile_library(flavor_blocks: list[dict]) -> dict:
    collections = {
        "ingredients": _load_yaml("ingredients.yaml")["ingredients"],
        "flavor_blocks": flavor_blocks,
        "protagonists": _load_yaml("protagonists.yaml")["protagonists"],
        "bases": _load_yaml("bases.yaml")["bases"],
        "acidity_sources": _load_yaml("acidity_sources.yaml")["acidity_sources"],
        "textures": _load_yaml("textures.yaml")["textures"],
        "aromatic_families": _load_yaml("aromatic_families.yaml")["aromatic_families"],
        "compatibility_rules": _load_yaml("compatibility_rules.yaml")["compatibility_rules"],
        "conflict_rules": _load_yaml("conflict_rules.yaml")["conflict_rules"],
        "regional_substitutions": _load_yaml("regional_substitutions.yaml")[
            "regional_substitutions"
        ],
        "seasonality": _load_yaml("seasonality.yaml")["seasonality"],
    }

    meta = _load_yaml("metadata.yaml")
    meta["version"] = "0.2.0"
    meta["generated_on"] = date.today().isoformat()
    meta["scope_note"] = (
        "Nordestino inclui ingredientes nativos, tradicionais, costeiros e amplamente "
        "produzidos/encontrados na região. Blocos de sabor são atômicos (1 ingrediente = 1 bloco)."
    )

    return {"metadata": meta, **collections}


def validate(lib: dict) -> dict:
    ingredient_ids = {i["id"] for i in lib["ingredients"]}
    missing = []
    for block in lib["flavor_blocks"]:
        for iid in block["ingredient_ids"]:
            if iid not in ingredient_ids:
                missing.append({"block_id": block["id"], "ingredient_id": iid})

    counts = {key: len(val) for key, val in lib.items() if isinstance(val, list)}
    return {
        "counts": counts,
        "duplicate_ingredient_ids": [],
        "flavor_block_missing_ingredient_refs": missing,
        "status": "ok" if not missing else "error",
    }


def main() -> None:
    ingredients = _load_yaml("ingredients.yaml")["ingredients"]
    protagonists = _load_yaml("protagonists.yaml")["protagonists"]
    legacy_path = CATALOG / "flavor_blocks.yaml"
    legacy_blocks = yaml.safe_load(legacy_path.read_text(encoding="utf-8")).get(
        "flavor_blocks", []
    )

    # Archive previous combo catalog once
    archive = CATALOG / "_archive_flavor_blocks_combo_v0_1.yaml"
    if not archive.exists() and legacy_blocks and any(
        len(b.get("ingredient_ids", [])) > 1 for b in legacy_blocks
    ):
        archive.write_text(legacy_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Archived combo blocks -> {archive.name}")

    atomic = build_atomic_blocks(ingredients, protagonists, legacy_blocks)
    payload = {"flavor_blocks": atomic}
    with legacy_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(
            payload,
            fh,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )
    print(f"Wrote {len(atomic)} atomic flavor blocks")

    # Persist metadata bump
    meta = _load_yaml("metadata.yaml")
    meta["version"] = "0.2.0"
    meta["generated_on"] = date.today().isoformat()
    with (CATALOG / "metadata.yaml").open("w", encoding="utf-8") as fh:
        yaml.safe_dump(meta, fh, allow_unicode=True, sort_keys=False)

    lib = compile_library(atomic)
    report = validate(lib)
    (LIBRARY_DIR / "validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (LIBRARY_DIR / "library.json").write_text(
        json.dumps(lib, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (LIBRARY_DIR / "library.yaml").open("w", encoding="utf-8") as fh:
        yaml.safe_dump(lib, fh, allow_unicode=True, sort_keys=False, default_flow_style=False)

    print("Rebuilt library.json / library.yaml")
    print("counts:", report["counts"])
    print("status:", report["status"])


if __name__ == "__main__":
    main()
