"""Parser de pedido em linguagem natural → CookingRequest."""

from __future__ import annotations

from app.agents import get_model
from langchain.agents import create_agent
from functools import lru_cache

from app.schemas import CookingRequest

REQUEST_PARSER_PROMPT = """
Você interpreta pedidos culinários em português e extrai um CookingRequest.

Regras:
- objective: intenção do prato em 1–2 frases.
- ingredients: lista do que a pessoa tem ou quer usar (sem quantidades inventadas
  demais; preserve o que foi dito).
  Normalize nomes regionais quando óbvio:
  "lagosta" → "lagosta vermelha";
  "camarão" → "camarão branco" se não especificado;
  "caranguejo" → "caranguejo uçá" se não especificado.
- servings: número de pessoas (padrão 4 se não informado; máximo 30).
- equipment: equipamentos mencionados. Se nenhum for citado, use
  ["Thermomix TM7", "churrasqueira"] como padrão da cozinha do chef.
  Se citar "TM7" use "Thermomix TM7".
- restrictions: alergias, o que evitar, preferências negativas.
- available_time_minutes: só se a pessoa limitar tempo.

Não invente ingredientes que não foram sugeridos ou implícitos pelo pedido.
Se o pedido for vago (ex.: "quero peixe"), use ingredients mínimos coerentes
com o que foi dito.
""".strip()


@lru_cache(maxsize=1)
def get_request_parser_agent():
    return create_agent(
        model=get_model(),
        system_prompt=REQUEST_PARSER_PROMPT,
        response_format=CookingRequest,
    )


def parse_cooking_request(user_text: str) -> CookingRequest:
    result = get_request_parser_agent().invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_text,
                }
            ]
        }
    )
    parsed = result.get("structured_response")
    if parsed is None:
        raise ValueError("Não foi possível interpretar o pedido.")
    return parsed
