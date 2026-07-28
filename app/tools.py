from pydantic import BaseModel, Field
from langchain.tools import tool

from app.rag import format_search_results, search_ceara_knowledge, search_knowledge


class IngredientAmount(BaseModel):
    name: str = Field(description="Nome do ingrediente")
    quantity_g: float = Field(description="Quantidade em gramas")


@tool
def search_recipes(query: str) -> str:
    """Busca nas fichas técnicas, técnicas e equipamentos do chef.

    Use antes de planejar o prato para reutilizar decisões, quantidades,
    temperaturas e combinações já validadas. Informe ingredientes,
    técnicas ou equipamentos na query.
    """
    documents = search_knowledge(query, k=4)
    return format_search_results(documents)


@tool
def search_ceara_recipes(query: str) -> str:
    """Busca no corpus regional do Ceará (ingredientes + fichas cearenses).

    Use quando o pedido envolver identidade cearense, ingredientes tipicos
    (carne de sol, coalho, cajuina, feijao verde, lagosta, caranguejo, etc.)
    ou combinacoes regionais.
    """
    documents = search_ceara_knowledge(query, k=5)
    return format_search_results(documents)


@tool
def thermomix_conversion(
    technique: str,
    quantity_g: int,
) -> str:
    """Converte uma técnica convencional para uma execução segura na TM7."""

    known_methods = {
        "emulsao": (
            "Começar em velocidade baixa e aumentar gradualmente. "
            "Controlar a temperatura para evitar separação."
        ),
        "infusao": (
            "Usar baixa velocidade, temperatura controlada e coar finamente."
        ),
        "pure": (
            "Cozinhar até completa maciez antes de processar. "
            "Evitar bater excessivamente ingredientes ricos em amido."
        ),
    }

    return known_methods.get(
        technique.lower(),
        "Não existe conversão validada para essa técnica.",
    )


@tool
def scale_recipe(
    original_servings: int,
    target_servings: int,
    ingredients: list[IngredientAmount],
) -> list[IngredientAmount]:
    """Escala ingredientes proporcionalmente pelo número de porções."""

    if original_servings <= 0 or target_servings <= 0:
        raise ValueError("O número de porções deve ser positivo.")

    factor = target_servings / original_servings

    return [
        IngredientAmount(
            name=item.name,
            quantity_g=round(item.quantity_g * factor, 1),
        )
        for item in ingredients
    ]


@tool
def equipment_capabilities() -> dict:
    """Retorna as capacidades e limitações dos equipamentos disponíveis."""

    return {
        "thermomix_tm7": [
            "triturar",
            "emulsionar",
            "aquecer com controle",
            "infusionar",
            "cozinhar lentamente",
        ],
        "forno_elettromec": [
            "assar",
            "gratinar",
            "convecção",
            "não possui vapor",
        ],
        "sous_vide": [
            "cocção precisa em baixa temperatura",
        ],
        "churrasqueira": [
            "grelhar",
            "defumar levemente",
            "finalizar sobre brasa",
        ],
    }
