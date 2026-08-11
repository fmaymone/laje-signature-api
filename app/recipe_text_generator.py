"""Gera RecipeImageImportDraft a partir de pedido em linguagem natural."""

from __future__ import annotations

from functools import lru_cache

from langchain.agents import create_agent

from api.schemas_recipe_import import RecipeImageImportDraft
from app.agents import get_model

RECIPE_TEXT_GENERATOR_PROMPT = """
Você cria receitas executáveis a partir de pedidos em português (ou traduzidos).

Regras:
- Gere uma receita prática e coerente com o pedido do usuário.
- Idioma de saída: SEMPRE português do Brasil (title, notes, ingredientes, passos).
- Não invente requisitos fora do pedido; complete só o necessário para a receita funcionar.
- Preferir NOMES EXATOS da lista de ingredientes do catálogo quando o item existir
  (ex.: use "Tomate" se estiver na lista, não "TOMATE" nem "tomate fresco" se "Tomate" cobrir).
  Só invente um nome novo se não houver equivalente razoável no catálogo.
- ingredients: name, quantity (realista), unit e notes opcional.
  Unidades: g, kg, ml, l, un, xicara, colher_sopa, colher_cha, dente, folha, ramo, a_gosto.
- steps: process curto (verbo/ação do passo), description com o detalhe; ids s1, s2, …
  Não use o nome da seção (ex. "ensopado") como process em todos os passos.
  Se o pedido não der tempos, duration_minutes=10 e time_before_service_minutes=0
  (estime uma sequência sensata se fizer sentido para o prato).
- lanes: se houver componentes (ensopado, molho, guarnição) ou linhas paralelas,
  crie uma lane por componente e use lane_id. Senão [{id:"main", name:"Principal"}].
- servings: do pedido; senão 4.
- notes: dica curta ou contexto do pedido; pode ser null.
- warnings: ambiguidades ou hipóteses (ex.: "Assumi molho estilo Big Mac caseiro").
- Não use blocos de sabor, composition_id nem estilo Compor — só a ficha do livro.

Responda no schema solicitado.
""".strip()


@lru_cache(maxsize=1)
def get_recipe_text_generator_agent():
    return create_agent(
        model=get_model(),
        system_prompt=RECIPE_TEXT_GENERATOR_PROMPT,
        response_format=RecipeImageImportDraft,
    )


def generate_recipe_from_text(
    *,
    user_prompt: str,
    catalog_names: list[str],
) -> RecipeImageImportDraft:
    text = user_prompt.strip()
    if not text:
        raise ValueError("Descreva a receita que você quer.")

    names = catalog_names[:200]
    catalog_block = ", ".join(names) if names else "(catálogo vazio)"

    result = get_recipe_text_generator_agent().invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Pedido do usuário:\n{text}\n\n"
                        f"Ingredientes do catálogo (prefira estes nomes quando couber):\n"
                        f"{catalog_block}"
                    ),
                }
            ]
        }
    )
    parsed = result.get("structured_response")
    if parsed is None:
        raise ValueError("Não foi possível gerar a receita.")
    if isinstance(parsed, RecipeImageImportDraft):
        return parsed
    return RecipeImageImportDraft.model_validate(parsed)
