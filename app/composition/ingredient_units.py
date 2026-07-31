"""Unidades, status de estoque e helpers de ingredientes."""

from __future__ import annotations

from typing import Literal

IngredientUnit = Literal[
    "g",
    "kg",
    "ml",
    "l",
    "un",
    "xicara",
    "colher_sopa",
    "colher_cha",
    "dente",
    "folha",
    "ramo",
    "a_gosto",
]

# Padrão de inventário culinário (MarketMan / restaurant inventory).
IngredientStockStatus = Literal[
    "in_stock",  # Em estoque
    "low_stock",  # Estoque baixo
    "out_of_stock",  # Faltando
    "on_order",  # Em pedido
]

UNIT_LABELS: dict[str, str] = {
    "g": "g",
    "kg": "kg",
    "ml": "ml",
    "l": "L",
    "un": "un",
    "xicara": "xícara",
    "colher_sopa": "colher (sopa)",
    "colher_cha": "colher (chá)",
    "dente": "dente",
    "folha": "folha",
    "ramo": "ramo",
    "a_gosto": "a gosto",
}

STATUS_LABELS: dict[str, str] = {
    "in_stock": "Em estoque",
    "low_stock": "Estoque baixo",
    "out_of_stock": "Faltando",
    "on_order": "Em pedido",
}

CATEGORY_DEFAULT_UNIT: dict[str, str] = {
    "peixe": "g",
    "carne": "g",
    "crustaceo": "g",
    "molusco": "g",
    "laticinio": "g",
    "gordura": "ml",
    "fruta_acida": "un",
    "fruta_doce": "un",
    "hortalica": "g",
    "erva_aromatica": "g",
    "condimento": "g",
    "cereal": "g",
    "leguminosa": "g",
    "castanha_semente": "g",
    "raiz_tuberculo": "g",
    "outro": "g",
    "seco": "g",
    "tempero": "g",
    "bebida": "ml",
}


def compute_stock_status(
    quantity: float,
    reorder_level: float,
    status_override: str | None = None,
) -> str:
    if status_override in {"in_stock", "low_stock", "out_of_stock", "on_order"}:
        return status_override
    if quantity <= 0:
        return "out_of_stock"
    if reorder_level > 0 and quantity <= reorder_level:
        return "low_stock"
    return "in_stock"


def default_unit_for_category(category: str) -> str:
    return CATEGORY_DEFAULT_UNIT.get(category, "g")
