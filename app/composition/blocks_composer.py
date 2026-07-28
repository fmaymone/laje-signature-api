"""Compositor determinístico v0.1 — blocos → compatibilidade → conflitos."""

from __future__ import annotations

from copy import deepcopy

from app.composition.library_v01 import index_library, load_library
from app.flavor_schemas import (
    DishArchitecture,
    SelectedBlock,
    SensoryProfile,
    TextureProfile,
)


SOFT_TEXTURES = {"cremoso", "macio", "suculento", "leve", "úmido", "umido", "doce"}
CRUNCH_TEXTURES = {
    "crocante",
    "tostado",
    "firme",
    "seco",
    "chips",
    "farofa",
    "granulado",
    "crosta",
}


def _normalize(text: str) -> str:
    table = str.maketrans(
        {
            "á": "a",
            "ã": "a",
            "â": "a",
            "à": "a",
            "é": "e",
            "ê": "e",
            "í": "i",
            "ó": "o",
            "ô": "o",
            "õ": "o",
            "ú": "u",
            "ç": "c",
        }
    )
    return text.lower().translate(table).replace("-", "_").replace(" ", "_")


def detect_protagonist_id(mentions: list[str]) -> str:
    idx = index_library()
    blob = " ".join(_normalize(m) for m in mentions)
    tokens = set(blob.replace(",", " ").split())

    best: tuple[int, str] | None = None

    def consider(candidate_id: str, names: list[str]) -> None:
        nonlocal best
        for name in names:
            token = _normalize(name)
            if not token:
                continue
            score = 0
            if token == blob or token in tokens:
                score = 100 + len(token)
            elif token in blob:
                score = 50 + len(token)
            else:
                # "lagosta" casa com "lagosta_vermelha" / "lagosta-vermelha"
                stem = token.split("_")[0]
                if stem and (stem in tokens or stem in blob):
                    score = 40 + len(stem)
            if score and (best is None or score > best[0]):
                best = (score, candidate_id)

    for protagonist in idx["protagonists"].values():
        ingredient = idx["ingredients"].get(protagonist["ingredient_id"], {})
        names = [
            protagonist["id"],
            protagonist.get("ingredient_id", ""),
            ingredient.get("name", ""),
            *ingredient.get("aliases", []),
        ]
        consider(protagonist["id"], names)

    if best:
        return best[1]

    for ingredient in idx["ingredients"].values():
        if "protagonista" not in ingredient.get("culinary_roles", []):
            continue
        names = [ingredient["id"], ingredient["name"], *ingredient.get("aliases", [])]
        consider(ingredient["id"], names)

    return "sirigado"


def _mention_tokens(mentions: list[str]) -> set[str]:
    tokens: set[str] = set()
    for mention in mentions:
        norm = _normalize(mention)
        tokens.add(norm)
        tokens.update(norm.replace(",", " ").split())
    return tokens


def _score_block(block: dict, protagonist_id: str, tokens: set[str]) -> float:
    score = 0.0
    compatible = block.get("compatible_protagonists", [])
    if protagonist_id in compatible:
        score += 10
    elif not compatible:
        score += 1

    for ingredient_id in block.get("ingredient_ids", []):
        if ingredient_id in tokens or any(
            ingredient_id in token or token in ingredient_id for token in tokens
        ):
            score += 3

    roles = set(block.get("culinary_roles", []))
    if "protagonista" in roles and protagonist_id in block.get("ingredient_ids", []):
        score += 5
    if "brasa" in roles and any("brasa" in t or "churras" in t for t in tokens):
        score += 2
    if "base" in roles and any(
        t in tokens for t in ("milho", "milho_verde", "macaxeira", "jerimum")
    ):
        score += 2
    return score


def select_flavor_blocks(
    *,
    protagonist_id: str,
    mentions: list[str],
    max_blocks: int = 4,
) -> dict:
    """Nó 1 — escolhe blocos a partir de flavor_blocks."""
    lib = load_library()
    idx = index_library()
    tokens = _mention_tokens(mentions + [protagonist_id])

    ranked = sorted(
        lib["flavor_blocks"],
        key=lambda block: _score_block(block, protagonist_id, tokens),
        reverse=True,
    )

    selected: list[dict] = []
    covered_roles: set[str] = set()

    for block in ranked:
        if _score_block(block, protagonist_id, tokens) <= 0 and selected:
            continue
        if protagonist_id not in block.get("compatible_protagonists", []) and selected:
            # After first block, still allow complementary if roles missing
            if not any(
                role not in covered_roles
                for role in block.get("culinary_roles", [])
                if role in {"acidez", "frescor", "textura", "molho", "aroma", "base"}
            ):
                continue

        new_roles = set(block.get("culinary_roles", [])) - covered_roles
        if selected and not new_roles and len(selected) >= 2:
            continue

        selected.append(block)
        covered_roles |= set(block.get("culinary_roles", []))
        if len(selected) >= max_blocks:
            break

    # Ensure at least one texture-ish if missing
    if not covered_roles.intersection({"textura", "brasa"}) and len(selected) < max_blocks:
        for block in ranked:
            if block in selected:
                continue
            if "textura" in block.get("culinary_roles", []):
                if (
                    protagonist_id in block.get("compatible_protagonists", [])
                    or not block.get("compatible_protagonists")
                ):
                    selected.append(block)
                    break

    sensory = _aggregate_sensory([b["target_sensory_profile"] for b in selected])
    textures = _collect_textures(selected)

    return {
        "protagonist_id": protagonist_id,
        "selected_blocks": selected,
        "covered_roles": sorted(covered_roles),
        "sensory": sensory,
        "texture_targets": textures,
        "notes": [
            f"Selecionados {len(selected)} blocos para protagonista '{protagonist_id}'."
        ],
    }


def _aggregate_sensory(profiles: list[dict]) -> dict[str, float]:
    if not profiles:
        return {key: 0.0 for key in SensoryProfile.model_fields}
    keys = SensoryProfile.model_fields.keys()
    totals = {key: 0.0 for key in keys}
    for profile in profiles:
        for key in keys:
            totals[key] += float(profile.get(key, 0))
    n = float(len(profiles))
    return {key: round(totals[key] / n, 2) for key in keys}


def _collect_textures(blocks: list[dict]) -> list[str]:
    textures: list[str] = []
    for block in blocks:
        for texture in block.get("texture_targets", []):
            if texture not in textures:
                textures.append(texture)
    return textures


def _soft_count(textures: list[str]) -> int:
    return sum(1 for texture in textures if _normalize(texture) in SOFT_TEXTURES or any(
        soft in _normalize(texture) for soft in SOFT_TEXTURES
    ))


def _crunch_count(textures: list[str]) -> int:
    return sum(
        1
        for texture in textures
        if any(crunch in _normalize(texture) for crunch in CRUNCH_TEXTURES)
    )


def apply_compatibility_rules(selection: dict) -> dict:
    """Nó 2 — avalia compatibility_rules e propõe/aplica correções."""
    lib = load_library()
    idx = index_library()
    selection = deepcopy(selection)
    sensory = selection["sensory"]
    textures = selection["texture_targets"]
    blocks = selection["selected_blocks"]
    protagonist_id = selection["protagonist_id"]
    protagonist = idx["protagonists"].get(protagonist_id, {})
    ingredient_ids = {
        ingredient_id
        for block in blocks
        for ingredient_id in block.get("ingredient_ids", [])
    }
    categories = {
        idx["ingredients"][iid]["category"]
        for iid in ingredient_ids
        if iid in idx["ingredients"]
    }
    base_ids = {
        base_id
        for block in blocks
        for base_id in block.get("recommended_base_ids", [])
    }
    roles = {role for block in blocks for role in block.get("culinary_roles", [])}

    triggered: list[dict] = []
    actions: list[str] = []

    soft = _soft_count(textures)
    crunch = _crunch_count(textures)

    context = {
        "fat": sensory.get("fat", 0),
        "acidity": sensory.get("acidity", 0),
        "freshness": sensory.get("freshness", 0),
        "saltiness": sensory.get("saltiness", 0),
        "aroma": sensory.get("aroma", 0),
        "soft_components": soft,
        "crunch_components": crunch,
        "protagonist_profile": protagonist.get("profile", ""),
        "protagonist_id": protagonist_id,
        "categories": categories,
        "ingredient_ids": ingredient_ids,
        "base_ids": base_ids,
        "roles": roles,
        "techniques": {
            role for role in roles if role in {"brasa", "grelha", "cura_leve"}
        },
        "sauce_or_juicy": 1
        if roles.intersection({"molho", "glace", "caldo", "aproveitamento"})
        or any("cremoso" in _normalize(t) for t in textures)
        else 0,
        "sauce_intensity": sensory.get("umami", 0) + sensory.get("fat", 0) / 2,
    }

    for rule in sorted(
        lib["compatibility_rules"],
        key=lambda item: item.get("priority", 0),
        reverse=True,
    ):
        if _rule_matches(rule.get("when", {}), context):
            triggered.append(rule)
            actions.append(rule["action"])

    # Auto-fix: try to add a complementary block for common gaps
    additions: list[dict] = []
    if any("acidez" in action.lower() or "ácido" in action.lower() for action in actions):
        addition = _find_block_with_role(
            lib["flavor_blocks"],
            protagonist_id,
            {"acidez", "frescor"},
            exclude={block["id"] for block in blocks},
        )
        if addition:
            additions.append(addition)
            actions.append(f"Bloco adicionado automaticamente: {addition['id']}")

    if any("textura" in action.lower() or "crocante" in action.lower() or "tostad" in action.lower() for action in actions):
        addition = _find_block_with_role(
            lib["flavor_blocks"],
            protagonist_id,
            {"textura"},
            exclude={block["id"] for block in blocks}
            | {item["id"] for item in additions},
        )
        if addition:
            additions.append(addition)
            actions.append(f"Bloco adicionado automaticamente: {addition['id']}")

    if additions:
        blocks = blocks + additions
        selection["selected_blocks"] = blocks
        selection["covered_roles"] = sorted(
            {role for block in blocks for role in block.get("culinary_roles", [])}
        )
        selection["sensory"] = _aggregate_sensory(
            [block["target_sensory_profile"] for block in blocks]
        )
        selection["texture_targets"] = _collect_textures(blocks)

    selection["compatibility_triggered"] = [
        {"id": rule["id"], "action": rule["action"], "priority": rule.get("priority")}
        for rule in triggered
    ]
    selection["compatibility_actions"] = actions
    selection["notes"] = selection.get("notes", []) + [
        f"Compatibilidade: {len(triggered)} regras acionadas."
    ]
    return selection


def _rule_matches(when: dict, context: dict) -> bool:
    if not when:
        return False

    if "fat_gte" in when and not (context["fat"] >= when["fat_gte"]):
        return False
    if "acidity_lt" in when and not (context["acidity"] < when["acidity_lt"]):
        return False
    if "freshness_lt" in when and not (context["freshness"] < when["freshness_lt"]):
        return False
    if "saltiness_lt" in when and not (context["saltiness"] < when["saltiness_lt"]):
        return False
    if "aroma_lt" in when and not (context["aroma"] < when["aroma_lt"]):
        return False
    if "soft_components_gte" in when and not (
        context["soft_components"] >= when["soft_components_gte"]
    ):
        return False
    if "crunch_components_lt" in when and not (
        context["crunch_components"] < when["crunch_components_lt"]
    ):
        return False
    if "sauce_or_juicy_components_lt" in when and not (
        context["sauce_or_juicy"] < when["sauce_or_juicy_components_lt"]
    ):
        return False
    if "sauce_intensity_gt" in when and not (
        context["sauce_intensity"] > when["sauce_intensity_gt"]
    ):
        return False
    if "protagonist_profile" in when:
        profile = _normalize(context["protagonist_profile"])
        needed = _normalize(when["protagonist_profile"])
        if needed not in profile and profile not in needed:
            # delicado matches delicado_firme
            if not (
                needed.startswith("delicado") and profile.startswith("delicado")
            ):
                return False
    if "protagonist_in" in when and context["protagonist_id"] not in when["protagonist_in"]:
        return False
    if "base_in" in when and not context["base_ids"].intersection(set(when["base_in"])):
        return False
    if "category_in" in when and not context["categories"].intersection(
        set(when["category_in"])
    ):
        return False
    if "category" in when and when["category"] not in context["categories"]:
        return False
    if "ingredient" in when and when["ingredient"] not in context["ingredient_ids"]:
        return False
    if "technique" in when and when["technique"] not in context["techniques"] and when[
        "technique"
    ] not in context["roles"]:
        return False

    # If we only had negative checks and nothing positive matched as a condition,
    # require at least one key handled — already enforced by falling through.
    return True


def _find_block_with_role(
    blocks: list[dict],
    protagonist_id: str,
    roles: set[str],
    exclude: set[str],
) -> dict | None:
    candidates = []
    for block in blocks:
        if block["id"] in exclude:
            continue
        if not roles.intersection(block.get("culinary_roles", [])):
            continue
        compatible = block.get("compatible_protagonists", [])
        if compatible and protagonist_id not in compatible:
            continue
        candidates.append(block)
    if not candidates:
        # relax protagonist filter
        candidates = [
            block
            for block in blocks
            if block["id"] not in exclude
            and roles.intersection(block.get("culinary_roles", []))
        ]
    return candidates[0] if candidates else None


def apply_conflict_rules(selection: dict) -> dict:
    """Nó 3 — detecta conflict_rules e resolve (remove/anota)."""
    lib = load_library()
    selection = deepcopy(selection)
    blocks = list(selection["selected_blocks"])
    ingredient_ids = {
        ingredient_id
        for block in blocks
        for ingredient_id in block.get("ingredient_ids", [])
    }
    roles = {role for block in blocks for role in block.get("culinary_roles", [])}
    textures = {_normalize(t) for t in selection.get("texture_targets", [])}
    tags = _selection_tags(ingredient_ids, roles, textures, blocks)

    triggered: list[dict] = []
    resolutions: list[str] = []
    removed: list[str] = []

    for rule in lib["conflict_rules"]:
        conflict_tokens = [_normalize(token) for token in rule.get("conflict", [])]
        hits = [token for token in conflict_tokens if _token_present(token, tags)]
        # Exige todos os tokens para regras curtas; maioria só se >=3
        needed = len(conflict_tokens) if len(conflict_tokens) <= 2 else len(conflict_tokens)
        if len(hits) < needed:
            continue

        triggered.append(rule)
        resolutions.append(f"{rule['id']}: {rule['resolution']}")

        # Remoções só em casos estruturais claros
        if rule["id"] == "multiple_purees":
            blocks, dropped = _dedupe_role_blocks(blocks, {"base"}, keep=1)
            removed.extend(dropped)
            tags = _selection_tags(
                {
                    ingredient_id
                    for block in blocks
                    for ingredient_id in block.get("ingredient_ids", [])
                },
                {role for block in blocks for role in block.get("culinary_roles", [])},
                {_normalize(t) for t in _collect_textures(blocks)},
                blocks,
            )
        elif rule["id"] == "multiple_farofas":
            blocks, dropped = _dedupe_role_blocks(blocks, {"textura"}, keep=1)
            removed.extend(dropped)
        elif rule["id"] == "coconut_plus_nata_overfat":
            blocks, dropped = _drop_blocks_with_ingredient(
                blocks, {"leite_de_coco", "nata"}, keep_one=True
            )
            removed.extend(dropped)
        elif rule["id"] == "acid_overload":
            blocks, dropped = _dedupe_role_blocks(
                blocks, {"acidez", "frescor"}, keep=2
            )
            removed.extend(dropped)

    if removed:
        # rebuild aggregates
        keep_ids = {block["id"] for block in blocks}
        blocks = [block for block in blocks if block["id"] in keep_ids]
        selection["selected_blocks"] = blocks
        selection["covered_roles"] = sorted(
            {role for block in blocks for role in block.get("culinary_roles", [])}
        )
        selection["sensory"] = _aggregate_sensory(
            [block["target_sensory_profile"] for block in blocks]
        )
        selection["texture_targets"] = _collect_textures(blocks)

    selection["conflicts_triggered"] = [
        {
            "id": rule["id"],
            "reason": rule["reason"],
            "resolution": rule["resolution"],
        }
        for rule in triggered
    ]
    selection["conflict_resolutions"] = resolutions
    selection["removed_blocks"] = removed
    selection["notes"] = selection.get("notes", []) + [
        f"Conflitos: {len(triggered)} regras; removidos: {removed or 'nenhum'}."
    ]
    return selection


def _selection_tags(
    ingredient_ids: set[str],
    roles: set[str],
    textures: set[str],
    blocks: list[dict],
) -> set[str]:
    tags = set(ingredient_ids) | {_normalize(role) for role in roles} | set(textures)
    for block in blocks:
        tags.add(block["id"])
        tags.add(_normalize(block.get("family", "")))

    if {"sirigado", "cioba", "camurim"} & ingredient_ids:
        tags.add("peixe_delicado")
    if "azeite_de_dende" in ingredient_ids:
        tags.add("dende")
    if "leite_de_coco" in ingredient_ids:
        tags.add("leite_de_coco")
    if "nata" in ingredient_ids:
        tags.add("nata")
    if "carne_de_sol" in ingredient_ids:
        tags.add("carne_de_sol")
    if "queijo_coalho" in ingredient_ids:
        tags.add("queijo_coalho")
    if "caju" in ingredient_ids:
        tags.add("caju")
    if "tamarindo" in ingredient_ids:
        tags.add("tamarindo")
    if {"camarao_branco", "lagosta", "lagostim"} & ingredient_ids:
        tags.add("crustaceo")

    base_blocks = [
        block for block in blocks if "base" in block.get("culinary_roles", [])
    ]
    if len(base_blocks) >= 2:
        tags.update({"pure_1", "pure_2"})

    texture_blocks = [
        block for block in blocks if "textura" in block.get("culinary_roles", [])
    ]
    farofa_like = sum(
        1
        for block in texture_blocks
        if any(
            token in _normalize(block["id"]) or token in " ".join(block.get("texture_targets", []))
            for token in ("farofa", "chips", "crosta")
        )
    )
    if farofa_like >= 2:
        tags.update({"farofa", "chips", "crosta_seca_em_excesso"})

    acid_blocks = [
        block
        for block in blocks
        if {"acidez", "frescor"} & set(block.get("culinary_roles", []))
    ]
    if len(acid_blocks) >= 3:
        tags.add("tres_fontes_acidas_intensas")

    # Gordura tripla só com evidência real
    fat_hits = sum(
        1
        for item in ("leite_de_coco", "nata", "manteiga_de_garrafa")
        if item in ingredient_ids
    )
    if fat_hits >= 3:
        tags.add("manteiga_de_garrafa_em_excesso")

    return {tag for tag in tags if tag}


def _token_present(token: str, tags: set[str]) -> bool:
    """Match exato ou prefixo conservador — evita falsos positivos."""
    if token in tags:
        return True
    # permite peixe_delicado ∈ tags already exact
    return False


def _dedupe_role_blocks(
    blocks: list[dict],
    roles: set[str],
    keep: int,
) -> tuple[list[dict], list[str]]:
    kept: list[dict] = []
    matched = 0
    removed: list[str] = []
    for block in blocks:
        if roles.intersection(block.get("culinary_roles", [])):
            matched += 1
            if matched <= keep:
                kept.append(block)
            else:
                removed.append(block["id"])
        else:
            kept.append(block)
    return kept, removed


def _drop_blocks_with_ingredient(
    blocks: list[dict],
    ingredients: set[str],
    keep_one: bool,
) -> tuple[list[dict], list[str]]:
    matched = [
        block
        for block in blocks
        if ingredients.intersection(block.get("ingredient_ids", []))
    ]
    if len(matched) <= 1:
        return blocks, []
    keep_id = matched[0]["id"] if keep_one else None
    removed = []
    kept = []
    for block in blocks:
        if block in matched and block["id"] != keep_id:
            removed.append(block["id"])
        else:
            kept.append(block)
    return kept, removed


def selection_to_architecture(selection: dict) -> DishArchitecture:
    blocks = selection["selected_blocks"]
    sensory = selection["sensory"]
    selected = [
        SelectedBlock(
            block_id=block["id"],
            role=_primary_role(block.get("culinary_roles", [])),
            chosen_form=block["name"],
            justification=(
                f"Família {block.get('family')}; papéis: "
                f"{', '.join(block.get('culinary_roles', []))}."
            ),
            ingredients=[],
        )
        for block in blocks
    ]
    soft = _soft_count(selection.get("texture_targets", []))
    crunch = _crunch_count(selection.get("texture_targets", []))
    contrast = 9.0 if soft and crunch else (3.0 if soft or crunch else 1.0)

    corrections = list(selection.get("compatibility_actions", []))
    corrections.extend(selection.get("conflict_resolutions", []))

    return DishArchitecture(
        title=f"{selection['protagonist_id']} — composição v0.1",
        concept=(
            "Arquitetura gerada pela Biblioteca Fernando Nordeste v0.1 "
            "via blocos + catálogos (base/acidez/textura/aroma) + "
            "compatibilidade + conflitos."
        ),
        protagonist=selection["protagonist_id"],
        family_id=blocks[0].get("family") if blocks else None,
        blocks=selected,
        sensory_estimate=SensoryProfile(**sensory),
        texture_estimate=TextureProfile(
            creamy=8 if soft else 0,
            crunchy=8 if crunch else 0,
            firm=6 if crunch else 0,
        ),
        texture_contrast=contrast,
        balance_corrections=corrections,
        composition_notes=selection.get("notes", []),
    )


def _primary_role(roles: list[str]) -> str:
    priority = [
        "protagonista",
        "base",
        "molho",
        "acidez",
        "textura",
        "aroma",
        "frescor",
        "brasa",
    ]
    for role in priority:
        if role in roles:
            return role
    return roles[0] if roles else "component"


def _pseudo_block_from_catalog(
    *,
    catalog: str,
    item: dict,
    role: str,
    ingredient_ids: list[str],
    sensory: dict | None = None,
    texture_targets: list[str] | None = None,
    notes: str = "",
) -> dict:
    profile = {
        "acidity": 0,
        "saltiness": 0,
        "sweetness": 0,
        "bitterness": 0,
        "umami": 0,
        "fat": 0,
        "heat": 0,
        "aroma": 0,
        "freshness": 0,
    }
    if sensory:
        profile.update(sensory)
    return {
        "id": f"catalog:{catalog}:{item['id']}",
        "name": item["name"],
        "family": f"catalog_{catalog}",
        "ingredient_ids": ingredient_ids,
        "culinary_roles": [role],
        "compatible_protagonists": [],
        "recommended_base_ids": [],
        "target_sensory_profile": profile,
        "texture_targets": texture_targets or [],
        "notes": notes or item.get("dose_guardrail") or item.get("best_use") or "",
        "source_catalog": catalog,
        "catalog_item_id": item["id"],
    }


def _protagonist_category(protagonist_id: str) -> str:
    idx = index_library()
    ingredient = idx["ingredients"].get(protagonist_id, {})
    return ingredient.get("category", "")


def _best_with_matches(base: dict, category: str) -> bool:
    mapping = {
        "peixe": "peixes",
        "crustaceo": "crustáceos",
        "molusco": "crustáceos",
        "carne": "carnes",
        "ave": "carnes",
        "vegetal": "vegetais",
        "tubérculo": "vegetais",
        "leguminosa": "vegetais",
    }
    wanted = mapping.get(category, "vegetais")
    best = [_normalize(x) for x in base.get("best_with", [])]
    return _normalize(wanted) in best or any(wanted in b for b in best)


def complete_from_catalogs(
    selection: dict,
    *,
    equipment: list[str] | None = None,
    current_month: int | None = None,
) -> dict:
    """Completa papéis faltantes com bases, acidez, texturas e aromas do catálogo."""
    from datetime import datetime

    selection = deepcopy(selection)
    idx = index_library()
    blocks = list(selection["selected_blocks"])
    roles = {role for block in blocks for role in block.get("culinary_roles", [])}
    textures = list(selection.get("texture_targets", []))
    sensory = dict(selection.get("sensory", {}))
    protagonist_id = selection["protagonist_id"]
    category = _protagonist_category(protagonist_id)
    equipment_blob = " ".join(_normalize(e) for e in (equipment or []))
    additions: list[dict] = []
    catalog_picks: list[dict] = []

    # —— Base ——
    if "base" not in roles:
        recommended: list[str] = []
        for block in blocks:
            recommended.extend(block.get("recommended_base_ids", []))
        chosen_base = None
        for base_id in recommended:
            if base_id in idx["bases"]:
                chosen_base = idx["bases"][base_id]
                break
        if chosen_base is None:
            candidates = sorted(
                idx["bases"].values(),
                key=lambda base: (
                    0 if _best_with_matches(base, category) else 1,
                    0
                    if base.get("primary_equipment")
                    and _normalize(base["primary_equipment"]) in equipment_blob
                    else 1,
                    base["id"],
                ),
            )
            chosen_base = candidates[0] if candidates else None
        if chosen_base:
            soft = [
                t
                for t in chosen_base.get("textures", [])
                if any(s in _normalize(t) for s in SOFT_TEXTURES)
            ]
            block = _pseudo_block_from_catalog(
                catalog="bases",
                item=chosen_base,
                role="base",
                ingredient_ids=chosen_base.get("ingredient_ids", []),
                sensory={"sweetness": 4, "fat": 3},
                texture_targets=chosen_base.get("textures", []),
                notes=f"best_with={chosen_base.get('best_with')}; eq={chosen_base.get('primary_equipment')}",
            )
            additions.append(block)
            catalog_picks.append(
                {"catalog": "bases", "id": chosen_base["id"], "name": chosen_base["name"]}
            )
            if soft:
                textures.extend(chosen_base.get("textures", []))

    # —— Acidez ——
    needs_acid = (
        "acidez" not in roles and "frescor" not in roles
    ) or float(sensory.get("acidity", 0)) < 5
    if needs_acid and not any(
        block.get("source_catalog") == "acidity_sources" for block in blocks + additions
    ):
        # Prefer citrus for seafood, fruity for meat
        preferred_styles = (
            ("aguda_fresca", "aguda_aromatica", "citrico")
            if category in {"peixe", "crustaceo", "molusco"}
            else ("frutada_aguda", "frutada_astringente", "fermentada_seca")
        )
        acids = list(idx["acidity_sources"].values())

        def acid_score(item: dict) -> tuple:
            style = _normalize(item.get("acidity_style", ""))
            pref = 0 if any(p in style for p in preferred_styles) else 1
            return (pref, -int(item.get("intensity", 0)), item["id"])

        acids.sort(key=acid_score)
        chosen_acid = acids[0]
        block = _pseudo_block_from_catalog(
            catalog="acidity_sources",
            item=chosen_acid,
            role="acidez",
            ingredient_ids=[chosen_acid["source_ingredient_id"]],
            sensory={
                "acidity": float(chosen_acid.get("intensity", 7)),
                "freshness": 7,
                "aroma": 5,
            },
            notes=chosen_acid.get("dose_guardrail", ""),
        )
        additions.append(block)
        catalog_picks.append(
            {
                "catalog": "acidity_sources",
                "id": chosen_acid["id"],
                "name": chosen_acid["name"],
                "style": chosen_acid.get("acidity_style"),
            }
        )

    # —— Textura ——
    soft_n = _soft_count(textures)
    crunch_n = _crunch_count(textures)
    if soft_n >= 1 and crunch_n < 1:
        textures_catalog = list(idx["textures"].values())

        def texture_score(item: dict) -> tuple:
            sig = _normalize(item.get("texture_signature", ""))
            crunch = 0 if any(c in sig for c in ("crocante", "crosta", "tostado")) else 1
            # prefer seafood-friendly textures
            ings = set(item.get("ingredient_ids", []))
            aligned = 0
            if category in {"peixe", "crustaceo"} and ings & {
                "milho_verde",
                "castanha_de_caju",
                "flocao_de_milho",
                "coco_fresco",
                "sirigado",
                "macaxeira",
            }:
                aligned = -1
            if category in {"carne", "ave"} and ings & {
                "queijo_coalho",
                "toucinho",
                "farinha_de_mandioca",
            }:
                aligned = -1
            return (crunch, aligned, item["id"])

        textures_catalog.sort(key=texture_score)
        chosen_texture = textures_catalog[0]
        sig = chosen_texture.get("texture_signature", "crocante")
        block = _pseudo_block_from_catalog(
            catalog="textures",
            item=chosen_texture,
            role="textura",
            ingredient_ids=chosen_texture.get("ingredient_ids", []),
            sensory={"aroma": 3, "fat": 2},
            texture_targets=[sig, "crocante", "tostado"],
            notes=chosen_texture.get("best_use", ""),
        )
        additions.append(block)
        catalog_picks.append(
            {
                "catalog": "textures",
                "id": chosen_texture["id"],
                "name": chosen_texture["name"],
                "signature": sig,
            }
        )

    # —— Aroma ——
    if "aroma" not in roles and "frescor" not in roles:
        aromatics = list(idx["aromatic_families"].values())

        def aroma_score(item: dict) -> tuple:
            signature = _normalize(item.get("signature", ""))
            # coastal for fish, sertaneja for meat
            if category in {"peixe", "crustaceo", "molusco"}:
                pref = 0 if any(
                    x in signature for x in ("fresco", "citrico", "frutado", "litoraneo")
                ) else 1
            else:
                pref = 0 if any(
                    x in signature for x in ("terroso", "quente", "sertaneja")
                ) else 1
            # avoid heavy dende on delicate fish unless already in blocks
            ings = set(item.get("ingredient_ids", []))
            penalty = 2 if "azeite_de_dende" in ings and category == "peixe" else 0
            return (pref + penalty, -int(item.get("intensity", 0)), item["id"])

        aromatics.sort(key=aroma_score)
        chosen_aroma = aromatics[0]
        block = _pseudo_block_from_catalog(
            catalog="aromatic_families",
            item=chosen_aroma,
            role="aroma",
            ingredient_ids=chosen_aroma.get("ingredient_ids", []),
            sensory={
                "aroma": float(chosen_aroma.get("intensity", 7)),
                "freshness": 7,
                "heat": 2,
            },
            notes=f"signature={chosen_aroma.get('signature')}; use={chosen_aroma.get('use')}",
        )
        additions.append(block)
        catalog_picks.append(
            {
                "catalog": "aromatic_families",
                "id": chosen_aroma["id"],
                "name": chosen_aroma["name"],
                "signature": chosen_aroma.get("signature"),
            }
        )

    if additions:
        blocks.extend(additions)
        selection["selected_blocks"] = blocks
        selection["covered_roles"] = sorted(
            {role for block in blocks for role in block.get("culinary_roles", [])}
        )
        selection["sensory"] = _aggregate_sensory(
            [block["target_sensory_profile"] for block in blocks]
        )
        selection["texture_targets"] = _collect_textures(blocks)

    # —— Sazonalidade / defeso ——
    month = current_month or datetime.now().month
    seasonality_notes: list[str] = []
    ingredient_ids = {
        ingredient_id
        for block in selection["selected_blocks"]
        for ingredient_id in block.get("ingredient_ids", [])
    }
    for ingredient_id in sorted(ingredient_ids):
        season = idx["seasonality"].get(ingredient_id)
        if not season:
            continue
        restriction = season.get("legal_restriction") or {}
        months = restriction.get("months") or []
        if months and month in months:
            seasonality_notes.append(
                f"ALERTA defeso/restrição ({ingredient_id}, mês {month}): "
                f"{restriction.get('note', 'Verificar norma vigente.')}"
            )
        peaks = season.get("peak_months") or []
        if peaks and month not in peaks:
            seasonality_notes.append(
                f"Fora do pico típico de {ingredient_id} "
                f"(picos={peaks}; confiança={season.get('confidence')}). "
                f"{season.get('notes', '')}"
            )
        elif season.get("availability") == "variable_wild_or_farmed":
            seasonality_notes.append(
                f"{ingredient_id}: disponibilidade variável "
                f"({season.get('confidence')}). {season.get('notes', '')}"
            )

    selection["catalog_picks"] = catalog_picks
    selection["seasonality_notes"] = seasonality_notes
    selection["notes"] = selection.get("notes", []) + [
        f"Catálogos: {len(catalog_picks)} adições "
        f"({', '.join(p['catalog'] for p in catalog_picks) or 'nenhuma'})."
    ] + seasonality_notes[:5]
    return selection


def compose_from_library_v01(
    *,
    mentions: list[str],
    max_blocks: int = 4,
    equipment: list[str] | None = None,
    current_month: int | None = None,
) -> tuple[dict, DishArchitecture]:
    """Pipeline: blocos → catálogos → compatibilidade → conflitos."""
    protagonist_id = detect_protagonist_id(mentions)
    selected = select_flavor_blocks(
        protagonist_id=protagonist_id,
        mentions=mentions,
        max_blocks=max_blocks,
    )
    completed = complete_from_catalogs(
        selected,
        equipment=equipment,
        current_month=current_month,
    )
    compatible = apply_compatibility_rules(completed)
    resolved = apply_conflict_rules(compatible)
    return resolved, selection_to_architecture(resolved)
