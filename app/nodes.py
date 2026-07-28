import json

import yaml

from app.agents import (
    fernando_critic_agent,
    technical_agent,
    technical_writer_agent,
)
from app.composition.blocks_composer import (
    apply_compatibility_rules,
    apply_conflict_rules,
    complete_from_catalogs,
    detect_protagonist_id,
    select_flavor_blocks,
    selection_to_architecture,
)
from app.composition.library_v01 import index_library
from app.flavor_schemas import RegionalReport, SensoryReport
from app.profile import load_profile
from app.rag import search_ceara_knowledge, search_knowledge
from app.schemas import FinalRecipe, RecipeDraft
from app.state import CulinaryState


def serialize(value) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump()

    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
    )


def retrieve_context(state: CulinaryState) -> dict:
    updates: dict = {}

    if not state.get("chef_profile"):
        profile = load_profile()
        updates["chef_profile"] = yaml.safe_dump(
            profile,
            allow_unicode=True,
            sort_keys=False,
        )

    request = state["request"]
    query = " ".join(
        [request.objective, *request.ingredients, *request.equipment]
    )

    try:
        docs = search_ceara_knowledge(query, k=4)
        if not docs:
            docs = search_knowledge(query, k=4)
        updates["relevant_recipes"] = [
            f"[{doc.metadata.get('source', '?')}]\n{doc.page_content.strip()}"
            for doc in docs
        ]
    except Exception as exc:  # noqa: BLE001
        updates["relevant_recipes"] = [f"(RAG indisponível: {exc})"]

    updates.setdefault("relevant_memories", state.get("relevant_memories", []))
    updates.setdefault("revision_count", state.get("revision_count", 0))
    updates.setdefault(
        "technical_revision_count", state.get("technical_revision_count", 0)
    )
    updates.setdefault("max_revisions", state.get("max_revisions", 3))
    return updates


def filter_regional(state: CulinaryState) -> dict:
    """Aplica substituições regionais da biblioteca v0.1."""
    request = state["request"]
    idx = index_library()
    substitutions = list(idx["regional_substitutions"].values())

    allowed: list[str] = []
    applied: list[str] = []
    rejected: list[str] = []
    notes: list[str] = []

    ingredient_lookup = {}
    for ingredient in idx["ingredients"].values():
        ingredient_lookup[ingredient["id"]] = ingredient
        ingredient_lookup[ingredient["name"].lower()] = ingredient
        for alias in ingredient.get("aliases", []):
            ingredient_lookup[alias.lower()] = ingredient

    for raw in request.ingredients:
        token = raw.lower()
        matched = None
        for key, ingredient in ingredient_lookup.items():
            if key in token or token in key:
                matched = ingredient
                break
        if matched:
            allowed.append(matched["name"])
            continue

        sub_hit = None
        for sub in substitutions:
            original = sub.get("original", "").lower()
            if original and original in token:
                sub_hit = sub
                break
        if sub_hit:
            option = sub_hit["regional_options"][0]
            allowed.append(option)
            applied.append(
                f"{sub_hit['original']} → {option} ({sub_hit.get('note', '')})"
            )
            continue

        rejected.append(raw)
        notes.append(f"Sem match/substituição v0.1 para '{raw}'.")

    return {
        "regional_report": RegionalReport(
            allowed_ingredients=sorted(set(allowed)),
            substitutions_applied=applied,
            rejected=rejected,
            notes=notes,
        )
    }


def select_blocks_node(state: CulinaryState) -> dict:
    """Nó determinístico 1: flavor_blocks."""
    request = state["request"]
    regional = state.get("regional_report")
    mentions = list(request.ingredients) + [request.objective, *request.equipment]
    if regional:
        mentions.extend(regional.allowed_ingredients)
    if fernando := state.get("fernando_review"):
        mentions.extend(fernando.required_changes)

    protagonist_id = detect_protagonist_id(mentions)
    selection = select_flavor_blocks(
        protagonist_id=protagonist_id,
        mentions=mentions,
        max_blocks=4,
    )
    return {"block_selection": selection}


def complete_catalogs_node(state: CulinaryState) -> dict:
    """Nó determinístico 1b: bases, acidez, texturas, aromas, sazonalidade."""
    request = state["request"]
    selection = state["block_selection"]
    completed = complete_from_catalogs(
        selection,
        equipment=request.equipment,
    )
    return {"block_selection": completed, "catalog_result": completed}


def apply_compatibility_node(state: CulinaryState) -> dict:
    """Nó determinístico 2: compatibility_rules."""
    selection = state.get("catalog_result") or state["block_selection"]
    result = apply_compatibility_rules(selection)
    return {"compatibility_result": result}


def apply_conflicts_node(state: CulinaryState) -> dict:
    """Nó determinístico 3: conflict_rules → arquitetura final."""
    selection = state["compatibility_result"]
    resolved = apply_conflict_rules(selection)
    architecture = selection_to_architecture(resolved)

    if fernando := state.get("fernando_review"):
        architecture.composition_notes.append(
            "Recomposição após crítico Fernando."
        )
        architecture.balance_corrections.extend(fernando.required_changes[:3])

    sensory_report = SensoryReport(
        sensory=architecture.sensory_estimate,
        texture=architecture.texture_estimate,
        texture_contrast=architecture.texture_contrast,
        corrections=architecture.balance_corrections,
        multi_function_notes=architecture.composition_notes,
    )
    return {
        "conflict_result": resolved,
        "architecture": architecture,
        "sensory_report": sensory_report,
    }


def compose_flavor_blocks(state: CulinaryState) -> dict:
    """Compat: executa blocos + catálogos + compat + conflitos."""
    updates = {}
    updates.update(select_blocks_node(state))
    state = {**state, **updates}
    updates.update(complete_catalogs_node(state))
    state = {**state, **updates}
    updates.update(apply_compatibility_node(state))
    state = {**state, **updates}
    updates.update(apply_conflicts_node(state))
    return updates


def write_executable_recipe(state: CulinaryState) -> dict:
    previous = []
    if technical := state.get("technical_review"):
        previous.append(f"Revisão técnica:\n{serialize(technical)}")
    if fernando := state.get("fernando_review"):
        previous.append(f"Crítico Fernando:\n{serialize(fernando)}")

    conflict = state.get("conflict_result") or {}
    prompt = f"""
PEDIDO:
{serialize(state["request"])}

PERFIL:
{state.get("chef_profile", "")}

RELATÓRIO REGIONAL:
{serialize(state.get("regional_report"))}

ARQUITETURA DE BLOCOS (obrigatória):
{serialize(state["architecture"])}

ESCOLHAS DE CATÁLOGO (bases / acidez / textura / aroma):
{serialize(conflict.get("catalog_picks", []))}

ALERTAS DE SAZONALIDADE / DEFESO:
{serialize(conflict.get("seasonality_notes", []))}

RELATÓRIO SENSORIAL:
{serialize(state.get("sensory_report"))}

FICHAS RELEVANTES:
{serialize(state.get("relevant_recipes", [])[:3])}

FEEDBACK ANTERIOR:
{chr(10).join(previous) or "Nenhum."}

Transforme a arquitetura em receita executável.
Incorpore as escolhas de catálogo como componentes/funções reais.
Respeite alertas de defeso (mencione verificação na compra se houver).
Não invente blocos fora da arquitetura/catálogo.
"""

    result = technical_writer_agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]}
    )
    executable = result["structured_response"]

    draft = RecipeDraft(
        title=executable.title,
        concept=executable.concept,
        components=executable.components,
        plating=executable.plating,
        rationale=executable.rationale + executable.block_mapping,
    )
    return {"draft": draft}


def review_technical_execution(state: CulinaryState) -> dict:
    prompt = f"""
PEDIDO:
{serialize(state["request"])}

ARQUITETURA:
{serialize(state.get("architecture"))}

RECEITA:
{serialize(state["draft"])}

Analise a execução técnica.
"""
    result = technical_agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]}
    )
    review = result["structured_response"]
    updates: dict = {"technical_review": review}
    if not review.approved:
        updates["technical_revision_count"] = (
            state.get("technical_revision_count", 0) + 1
        )
    return updates


def review_as_fernando(state: CulinaryState) -> dict:
    prompt = f"""
PERFIL:
{state.get("chef_profile", "")}

MEMÓRIAS:
{serialize(state.get("relevant_memories", []))}

ARQUITETURA DE BLOCOS:
{serialize(state.get("architecture"))}

SENSORIAL:
{serialize(state.get("sensory_report"))}

RECEITA:
{serialize(state["draft"])}

REVISÃO TÉCNICA:
{serialize(state.get("technical_review"))}

Essa composição parece Fernando?
"""
    result = fernando_critic_agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]}
    )
    return {
        "fernando_review": result["structured_response"],
        "revision_count": state.get("revision_count", 0) + 1,
    }


def finalize_recipe(state: CulinaryState) -> dict:
    draft = state["draft"]
    fernando_review = state["fernando_review"]
    technical_review = state["technical_review"]
    architecture = state.get("architecture")

    warning = None
    if not (fernando_review.approved and fernando_review.score >= 8):
        warning = (
            "Finalizado após limite de revisões. "
            f"Score: {fernando_review.score}. "
            f"Pendências: {'; '.join(fernando_review.required_changes) or 'nenhuma'}."
        )

    why = list(fernando_review.strengths)
    if architecture:
        why.append(
            f"Família de sabor: {architecture.family_id}; "
            f"blocos: {', '.join(b.block_id for b in architecture.blocks)}."
        )

    final_recipe = FinalRecipe(
        title=draft.title,
        concept=draft.concept,
        servings=state["request"].servings,
        components=draft.components,
        equipment=state["request"].equipment,
        mise_en_place=[
            f"{component.name}: {', '.join(component.ingredients)}"
            for component in draft.components
        ],
        timeline=technical_review.timing_notes,
        plating=draft.plating,
        critical_points=[
            point
            for component in draft.components
            for point in component.critical_points
        ]
        + technical_review.safety_notes,
        substitutions=(
            state["regional_report"].substitutions_applied
            if state.get("regional_report")
            else []
        ),
        conservation=[],
        why_this_matches_fernando=why,
        revision_warning=warning,
    )
    return {"final_recipe": final_recipe}


# Compat: antigo nome create_recipe
create_recipe = write_executable_recipe
