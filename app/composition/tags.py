"""Tags de domínio (família, técnica): id + título."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator


FAMILY_TITLES: dict[str, str] = {
    "agreste": "Agreste",
    "litoral": "Litoral",
    "litoral_sertao": "Litoral · Sertão",
    "mata": "Mata",
    "nordeste": "Nordeste",
    "sertao": "Sertão",
}

TECHNIQUE_TITLES: dict[str, str] = {
    "assar": "Assar",
    "baixa_temperatura": "Baixa temperatura",
    "brasa": "Brasa",
    "caldo": "Caldo",
    "caldo_com_aparas": "Caldo com aparas",
    "caldo_com_cascas": "Caldo com cascas",
    "caramelizar": "Caramelizar",
    "conservar": "Conservar",
    "cozimento_controlado": "Cozimento controlado",
    "cozimento_curto": "Cozimento curto",
    "cozinhar": "Cozinhar",
    "cru": "Cru",
    "cura_leve": "Cura leve",
    "deep_fry": "Deep fry",
    "desfiar": "Desfiar",
    "emulsionar": "Emulsionar",
    "ensopado": "Ensopado",
    "fermentar": "Fermentar",
    "finalizar": "Finalizar",
    "forno": "Forno",
    "fritar": "Fritar",
    "glacear": "Glacear",
    "gratinar": "Gratinar",
    "grelha": "Grelha",
    "grelhar": "Grelhar",
    "hidratar": "Hidratar",
    "infusionar": "Infusionar",
    "oleo_verde": "Óleo verde",
    "panela": "Panela",
    "poach": "Poach",
    "processar": "Processar",
    "reduzir": "Reduzir",
    "refogar": "Refogar",
    "roast": "Roast",
    "saltear": "Saltear",
    "saute": "Sauté",
    "steam": "Steam",
    "stir_fry": "Stir fry",
    "tostar": "Tostar",
    "triturar": "Triturar",
}


class Tag(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)

    @field_validator("id", mode="before")
    @classmethod
    def _normalize_id(cls, value: Any) -> str:
        return slugify_tag(str(value or ""))


def slugify_tag(value: str) -> str:
    text = value.strip().lower()
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
    text = text.translate(table)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")[:120]


def humanize_tag_id(tag_id: str) -> str:
    return tag_id.replace("_", " ").strip().title()


def title_for(tag_id: str, catalog: dict[str, str] | None = None) -> str:
    if catalog and tag_id in catalog:
        return catalog[tag_id]
    if tag_id in FAMILY_TITLES:
        return FAMILY_TITLES[tag_id]
    if tag_id in TECHNIQUE_TITLES:
        return TECHNIQUE_TITLES[tag_id]
    return humanize_tag_id(tag_id)


def coerce_tag(value: Any, *, catalog: dict[str, str] | None = None) -> Tag | None:
    if value is None:
        return None
    if isinstance(value, Tag):
        tag_id = slugify_tag(value.id)
        if not tag_id:
            return None
        title = (value.title or "").strip() or title_for(tag_id, catalog)
        return Tag(id=tag_id, title=title)
    if isinstance(value, dict):
        raw_id = value.get("id") or value.get("title") or ""
        tag_id = slugify_tag(str(raw_id))
        if not tag_id:
            return None
        raw_title = value.get("title")
        title = str(raw_title).strip() if raw_title else title_for(tag_id, catalog)
        return Tag(id=tag_id, title=title or title_for(tag_id, catalog))
    tag_id = slugify_tag(str(value))
    if not tag_id:
        return None
    return Tag(id=tag_id, title=title_for(tag_id, catalog))


def coerce_tag_list(value: Any, *, catalog: dict[str, str] | None = None) -> list[Tag]:
    if value is None:
        return []
    if isinstance(value, (str, dict, Tag)):
        items = [value]
    elif isinstance(value, list):
        items = value
    else:
        return []

    seen: set[str] = set()
    result: list[Tag] = []
    for item in items:
        tag = coerce_tag(item, catalog=catalog)
        if tag is None or tag.id in seen:
            continue
        seen.add(tag.id)
        result.append(tag)
    return result


def tag_id(value: Any) -> str:
    tag = coerce_tag(value)
    return tag.id if tag else ""


def tag_as_dict(value: Any, *, catalog: dict[str, str] | None = None) -> dict[str, str] | None:
    tag = coerce_tag(value, catalog=catalog)
    return tag.model_dump() if tag else None


def tags_as_dicts(value: Any, *, catalog: dict[str, str] | None = None) -> list[dict[str, str]]:
    return [tag.model_dump() for tag in coerce_tag_list(value, catalog=catalog)]


def normalize_block_tags(block: dict) -> dict:
    """Garante family Tag e techniques list[Tag] no dict do bloco."""
    family = coerce_tag(block.get("family"), catalog=FAMILY_TITLES)
    if family is None:
        family = Tag(id="nordeste", title=FAMILY_TITLES["nordeste"])
    block["family"] = family.model_dump()
    block["techniques"] = tags_as_dicts(block.get("techniques"), catalog=TECHNIQUE_TITLES)
    return block
