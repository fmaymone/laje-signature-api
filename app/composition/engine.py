"""Motor determinístico de composição por blocos de sabor nordestinos."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from app.flavor_schemas import (
    DishArchitecture,
    FlavorBlock,
    FlavorFamily,
    NordesteIngredient,
    RegionalReport,
    SelectedBlock,
    SensoryProfile,
    SensoryReport,
    Substitution,
    TextureProfile,
)

_NORDDESTE = (
    Path(__file__).resolve().parent.parent.parent
    / "knowledge"
    / "_archive"
    / "nordeste_mvp"
)

REQUIRED_ROLES = ("protagonist", "base", "sauce", "acidity", "texture", "aroma")


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


@lru_cache(maxsize=1)
def load_ingredients() -> dict[str, NordesteIngredient]:
    data = _load_yaml(_NORDDESTE / "ingredients.yaml")
    items = {}
    for raw in data.get("ingredients", []):
        ingredient = NordesteIngredient.model_validate(raw)
        items[ingredient.id] = ingredient
        items[ingredient.name.lower()] = ingredient
        for alias in ingredient.aliases:
            items[alias.lower()] = ingredient
    return items


@lru_cache(maxsize=1)
def load_blocks() -> dict[str, FlavorBlock]:
    data = _load_yaml(_NORDDESTE / "flavor_blocks.yaml")
    return {
        block.id: block
        for block in (
            FlavorBlock.model_validate(raw) for raw in data.get("blocks", [])
        )
    }


@lru_cache(maxsize=1)
def load_families() -> dict[str, FlavorFamily]:
    data = _load_yaml(_NORDDESTE / "families.yaml")
    return {
        family.id: family
        for family in (
            FlavorFamily.model_validate(raw) for raw in data.get("families", [])
        )
    }


@lru_cache(maxsize=1)
def load_substitutions() -> list[Substitution]:
    data = _load_yaml(_NORDDESTE / "substitutions.yaml")
    return [Substitution.model_validate(raw) for raw in data.get("substitutions", [])]


def reset_library_cache() -> None:
    load_ingredients.cache_clear()
    load_blocks.cache_clear()
    load_families.cache_clear()
    load_substitutions.cache_clear()


def _normalize(text: str) -> str:
    return (
        text.lower()
        .replace("á", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )


def detect_protagonist(ingredient_mentions: list[str]) -> str | None:
    ingredients = load_ingredients()
    protagonists = [
        ing
        for ing in {id(i): i for i in ingredients.values()}.values()
        if "protagonist" in ing.roles
    ]
    blob = " ".join(_normalize(x) for x in ingredient_mentions)
    for ingredient in sorted(protagonists, key=lambda i: len(i.name), reverse=True):
        names = [ingredient.name, ingredient.id, *ingredient.aliases]
        if any(_normalize(name) in blob for name in names if name):
            return ingredient.name
    return None


def apply_regional_filter(
    requested_ingredients: list[str],
) -> RegionalReport:
    ingredients = load_ingredients()
    substitutions = load_substitutions()
    sub_map = {
        _normalize(sub.from_ingredient): sub for sub in substitutions
    }

    allowed: list[str] = []
    applied: list[str] = []
    rejected: list[str] = []
    notes: list[str] = []

    for raw in requested_ingredients:
        token = raw.split(",")[0].strip()
        # remove quantidades simples
        for prefix in ("1,5 kg de ", "1.5 kg de ", "kg de ", "g de "):
            if _normalize(token).startswith(_normalize(prefix)):
                token = token[len(prefix) :]
        # strip leading numbers
        parts = token.split()
        while parts and any(ch.isdigit() for ch in parts[0]):
            parts = parts[1:]
        if parts and parts[0].lower() in {"de", "do", "da"}:
            parts = parts[1:]
        cleaned = " ".join(parts) if parts else token

        key = _normalize(cleaned)
        if key in {_normalize(k) for k in ingredients}:
            match = next(
                (
                    ingredients[k]
                    for k in ingredients
                    if _normalize(k) == key
                ),
                None,
            )
            if match:
                allowed.append(match.name)
                continue

        if key in sub_map:
            sub = sub_map[key]
            allowed.append(sub.to_ingredient)
            applied.append(
                f"{sub.from_ingredient} → {sub.to_ingredient} ({sub.reason})"
            )
            continue

        # partial match against library
        partial = next(
            (
                ing
                for ing in {id(i): i for i in ingredients.values()}.values()
                if _normalize(ing.name) in key or key in _normalize(ing.name)
            ),
            None,
        )
        if partial:
            allowed.append(partial.name)
            continue

        rejected.append(raw)
        notes.append(
            f"'{raw}' não está na biblioteca nordestina e não tem substituição cadastrada."
        )

    return RegionalReport(
        allowed_ingredients=sorted(set(allowed)),
        substitutions_applied=applied,
        rejected=rejected,
        notes=notes,
    )


def _weighted_mean(profiles: list[tuple[SensoryProfile, float]]) -> SensoryProfile:
    if not profiles:
        return SensoryProfile()
    fields = SensoryProfile.model_fields.keys()
    totals = {field: 0.0 for field in fields}
    weight_sum = 0.0
    for profile, weight in profiles:
        weight_sum += weight
        data = profile.model_dump()
        for field in fields:
            totals[field] += data[field] * weight
    if weight_sum == 0:
        return SensoryProfile()
    return SensoryProfile(**{field: round(totals[field] / weight_sum, 2) for field in fields})


def _texture_mean(profiles: list[tuple[TextureProfile, float]]) -> TextureProfile:
    if not profiles:
        return TextureProfile()
    fields = TextureProfile.model_fields.keys()
    totals = {field: 0.0 for field in fields}
    weight_sum = 0.0
    for profile, weight in profiles:
        weight_sum += weight
        data = profile.model_dump()
        for field in fields:
            totals[field] += data[field] * weight
    if weight_sum == 0:
        return TextureProfile()
    return TextureProfile(**{field: round(totals[field] / weight_sum, 2) for field in fields})


def texture_contrast(texture: TextureProfile) -> float:
    soft = max(texture.creamy, texture.tender, texture.juicy)
    hard = max(texture.crunchy, texture.crispy, texture.firm)
    return round(min(10.0, abs(hard - soft) + min(soft, hard) * 0.3), 2)


def texture_contrast_from_blocks(
    profiles: list[TextureProfile],
) -> float:
    """Alto quando há polo macio E polo crocante/firme no prato."""
    if not profiles:
        return 0.0
    soft = max(max(p.creamy, p.tender, p.juicy) for p in profiles)
    hard = max(max(p.crunchy, p.crispy, p.firm) for p in profiles)
    if soft >= 4 and hard >= 4:
        return round(min(10.0, (soft + hard) / 2 + 1.5), 2)
    # monotextura
    return round(min(3.0, max(soft, hard) * 0.35), 2)


def evaluate_balance(
    sensory: SensoryProfile,
    texture: TextureProfile,
    *,
    protagonist_name: str | None = None,
    component_count: int = 0,
    selected_roles: list[str] | None = None,
) -> SensoryReport:
    corrections: list[str] = []
    multi: list[str] = []
    roles = selected_roles or []

    if sensory.fat >= 7 and sensory.acidity < 5:
        corrections.append(
            "Adicionar uma fonte de acidez clara ou reduzir a gordura."
        )

    if sensory.sweetness >= 6 and sensory.acidity < 5 and sensory.bitterness < 3:
        corrections.append("O prato está doce e arredondado demais.")

    if texture.creamy >= 6 and max(texture.crunchy, texture.crispy) < 3:
        corrections.append(
            "Adicionar um componente seco, crocante ou tostado."
        )

    ingredients = load_ingredients()
    if protagonist_name:
        protagonist = ingredients.get(protagonist_name) or ingredients.get(
            protagonist_name.lower()
        )
        if protagonist and protagonist.delicacy >= 7 and sensory.umami >= 8 and sensory.fat >= 7:
            corrections.append(
                "O molho pode esconder o ingrediente principal delicado."
            )
        if protagonist_name.lower() in {"carne de sol", "queijo coalho"} and sensory.saltiness >= 7:
            corrections.append(
                "Orçamento de sal alto: reduzir sal adicional e reforçar acidez."
            )

    if component_count > 6:
        corrections.append("Simplificar o prato e combinar funções.")

    # Multifunção: se acidity e aroma cobertos pelo mesmo bloco tipicamente
    if "acidity" in roles and "aroma" in roles:
        multi.append(
            "Acidez e aroma podem estar no mesmo bloco fresco (ex.: vinagrete)."
        )

    contrast = texture_contrast(texture)
    if contrast < 4:
        corrections.append("Aumentar contraste de textura entre base e acabamento.")

    return SensoryReport(
        sensory=sensory,
        texture=texture,
        texture_contrast=contrast,
        corrections=corrections,
        multi_function_notes=multi,
    )


def _pick_block_for_role(
    role: str,
    blocks: dict[str, FlavorBlock],
    preferred_ids: list[str],
    protagonist: str,
    already: set[str],
) -> FlavorBlock | None:
    candidates: list[FlavorBlock] = []
    for block_id in preferred_ids:
        block = blocks.get(block_id)
        if not block or block.id in already:
            continue
        if role not in block.culinary_roles:
            continue
        if (
            block.compatible_protagonists
            and protagonist.lower()
            not in [p.lower() for p in block.compatible_protagonists]
            and role == "protagonist"
            and protagonist.lower() not in block.name.lower()
        ):
            # for protagonist role, allow if name matches
            if role == "protagonist" and protagonist.lower() not in " ".join(
                block.compatible_protagonists
            ).lower():
                continue
        candidates.append(block)

    if not candidates:
        for block in blocks.values():
            if block.id in already:
                continue
            if role not in block.culinary_roles:
                continue
            if block.compatible_protagonists:
                if protagonist.lower() not in [
                    p.lower() for p in block.compatible_protagonists
                ]:
                    continue
            # conflicts with already selected
            if any(c in already for c in block.conflicting_blocks):
                continue
            candidates.append(block)

    if not candidates:
        return None

    # prefer higher regional availability
    candidates.sort(key=lambda b: b.regional_availability, reverse=True)
    return candidates[0]


def _conflicts(selected: list[FlavorBlock], candidate: FlavorBlock) -> bool:
    selected_ids = {block.id for block in selected}
    if any(c in selected_ids for c in candidate.conflicting_blocks):
        return True
    for block in selected:
        if candidate.id in block.conflicting_blocks:
            return True
    return False


def choose_family(protagonist: str, mentions: list[str]) -> FlavorFamily:
    families = load_families()
    blob = _normalize(" ".join([protagonist, *mentions]))
    prot = _normalize(protagonist)

    fish = {"sirigado", "pargo", "cioba", "camarao", "camarão", "lagosta", "peixe"}
    scoring: list[tuple[int, FlavorFamily]] = []
    for family in families.values():
        score = 0
        for token in family.core + family.supports:
            if _normalize(token) in blob:
                score += 2
        if prot in " ".join(_normalize(x) for x in family.core + family.supports):
            score += 3

        if prot in fish or any(x in blob for x in fish):
            if family.id == "mar_coco_citrico":
                score += 8
        if "carne de sol" in prot:
            if family.id == "carne_sol_nata_fruta_acida":
                score += 10
        if "porco" in prot:
            if family.id == "porco_rapadura_fruta_acida":
                score += 10
        if "jerimum" in prot or "abobora" in prot:
            if family.id == "jerimum_castanha_fermentado":
                score += 10
        if prot in {"milho"} and family.id == "milho_coalho_pimenta":
            score += 8
        elif "milho" in blob and family.id == "milho_coalho_pimenta":
            score += 2

        scoring.append((score, family))

    scoring.sort(key=lambda item: item[0], reverse=True)
    return scoring[0][1]


def compose_architecture(
    *,
    protagonist: str,
    mentions: list[str],
    max_blocks: int = 5,
) -> DishArchitecture:
    """Seleciona até 1 bloco por função essencial, priorizando famílias."""
    blocks = load_blocks()
    family = choose_family(protagonist, mentions)
    preferred = family.preferred_block_ids

    selected: list[FlavorBlock] = []
    role_assignment: list[tuple[str, FlavorBlock]] = []

    # Always pick protagonist first
    for role in REQUIRED_ROLES:
        block = _pick_block_for_role(
            role, blocks, preferred, protagonist, {b.id for b in selected}
        )
        if block is None:
            continue
        if _conflicts(selected, block):
            # try next preferred
            continue
        # avoid duplicate blocks covering multiple roles already selected
        if block.id in {b.id for b in selected}:
            continue
        selected.append(block)
        role_assignment.append((role, block))
        if len(selected) >= max_blocks:
            break

    # Ensure acidity somehow covered — prefer multifunction block already in
    roles_covered = {role for role, _ in role_assignment}
    if "acidity" not in roles_covered:
        for block in selected:
            if "acidity" in block.culinary_roles:
                roles_covered.add("acidity")
                break

    selected_blocks: list[SelectedBlock] = []
    for role, block in role_assignment:
        form = block.forms[0] if block.forms else block.name
        selected_blocks.append(
            SelectedBlock(
                block_id=block.id,
                role=role,
                chosen_form=form,
                justification=(
                    f"Função {role} via bloco '{block.name}' "
                    f"(família {family.name})."
                ),
                ingredients=block.ingredients,
            )
        )

    weighted = []
    textures = []
    for role, block in role_assignment:
        weight = 1.4 if role == "protagonist" else 1.0
        if role == "sauce":
            weight = 1.2
        weighted.append((block.sensory_profile, weight))
        textures.append((block.texture_profile, weight))

    sensory = _weighted_mean(weighted)
    texture = _texture_mean(textures)
    contrast = texture_contrast_from_blocks([t for t, _ in textures])
    report = evaluate_balance(
        sensory,
        texture,
        protagonist_name=protagonist,
        component_count=len(selected_blocks),
        selected_roles=[role for role, _ in role_assignment],
    )
    report.texture_contrast = contrast
    if contrast < 4 and not any(
        "contraste de textura" in c.lower() for c in report.corrections
    ):
        report.corrections.append(
            "Aumentar contraste de textura entre base e acabamento."
        )
    elif contrast >= 4:
        report.corrections = [
            c
            for c in report.corrections
            if "contraste de textura" not in c.lower()
        ]

    # Auto-correção leve: se falta crocância, tentar inserir texture block
    if any("crocante" in c.lower() or "tostado" in c.lower() for c in report.corrections):
        if "texture" not in roles_covered:
            texture_block = _pick_block_for_role(
                "texture",
                blocks,
                preferred,
                protagonist,
                {b.id for b in selected},
            )
            if texture_block and not _conflicts(selected, texture_block):
                selected.append(texture_block)
                selected_blocks.append(
                    SelectedBlock(
                        block_id=texture_block.id,
                        role="texture",
                        chosen_form=(
                            texture_block.forms[0]
                            if texture_block.forms
                            else texture_block.name
                        ),
                        justification="Correção automática: contraste de textura.",
                        ingredients=texture_block.ingredients,
                    )
                )
                weighted.append((texture_block.sensory_profile, 1.0))
                textures.append((texture_block.texture_profile, 1.0))
                sensory = _weighted_mean(weighted)
                texture = _texture_mean(textures)
                contrast = texture_contrast_from_blocks([t for t, _ in textures])
                report = evaluate_balance(
                    sensory,
                    texture,
                    protagonist_name=protagonist,
                    component_count=len(selected_blocks),
                    selected_roles=[b.role for b in selected_blocks],
                )
                report.texture_contrast = contrast
                if contrast >= 4:
                    report.corrections = [
                        c
                        for c in report.corrections
                        if "contraste de textura" not in c.lower()
                        and "crocante" not in c.lower()
                    ]

    title = f"{protagonist.title()} — composição {family.name}"
    concept = (
        f"Arquitetura baseada na família '{family.name}' com "
        f"{len(selected_blocks)} blocos de função definida."
    )

    return DishArchitecture(
        title=title,
        concept=concept,
        protagonist=protagonist,
        family_id=family.id,
        blocks=selected_blocks,
        sensory_estimate=report.sensory,
        texture_estimate=report.texture,
        texture_contrast=report.texture_contrast,
        balance_corrections=report.corrections,
        composition_notes=report.multi_function_notes
        + [f"Família escolhida: {family.name}"],
    )
