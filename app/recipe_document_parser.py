"""Parser de receita a partir de texto de documento (PDF com texto)."""

from __future__ import annotations

from functools import lru_cache

from langchain.agents import create_agent

from api.schemas_recipe_import import RecipeImageImportDraft
from app.agents import get_model

RECIPE_DOCUMENT_PARSER_PROMPT = """
Você transcreve receitas a partir do texto extraído de um documento (PDF).

Regras absolutas:
- Extraia APENAS o que está no texto. Não invente ingredientes, passos, tempos,
  porções ou técnicas que não apareçam.
- Idioma de saída: SEMPRE português do Brasil.
  Se o texto estiver em inglês (ou outro idioma), traduza title, notes, nomes de
  ingredientes, process, description e avisos para português.
  Preserve o sentido e as quantidades; não reinterpretar a receita.
  Em warnings, inclua "Traduzido do inglês" (ou idioma) quando houver tradução.
- Se algo estiver ambíguo ou cortado, omita ou use warnings.
- title, notes, servings, ingredients, steps, lanes: mesmas regras do schema
  (unidades: g, kg, ml, l, un, xicara, colher_sopa, colher_cha, dente, folha,
  ramo, a_gosto; steps com ids s1, s2, …).
- lanes: se a receita tiver componentes/seções (ex.: ensopado, molho, guarnição),
  crie uma lane por componente (id slug, name legível) e atribua lane_id nos
  passos. Não repita o nome da seção em `process` de todos os passos.
- process: verbo/ação curta daquele passo (refogar, temperar, servir), não o
  nome da seção inteira.
- timings só se estiverem no texto; senão duration_minutes=10 e
  time_before_service_minutes=0.

Responda no schema solicitado. Não reinterpretar o estilo culinário.
""".strip()


@lru_cache(maxsize=1)
def get_recipe_document_parser_agent():
    return create_agent(
        model=get_model(),
        system_prompt=RECIPE_DOCUMENT_PARSER_PROMPT,
        response_format=RecipeImageImportDraft,
    )


def parse_recipe_from_document_text(document_text: str) -> RecipeImageImportDraft:
    text = document_text.strip()
    if not text:
        raise ValueError("PDF sem texto legível.")
    # Limita payload para o modelo
    if len(text) > 12000:
        text = text[:12000] + "\n\n[…texto truncado…]"

    result = get_recipe_document_parser_agent().invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Transcreva fielmente a receita deste texto de documento "
                        "para o schema solicitado. Se estiver em inglês ou outro "
                        "idioma, traduza tudo para português do Brasil.\n\n"
                        f"{text}"
                    ),
                }
            ]
        }
    )
    parsed = result.get("structured_response")
    if parsed is None:
        raise ValueError("Não foi possível ler a receita no PDF.")
    if isinstance(parsed, RecipeImageImportDraft):
        return parsed
    return RecipeImageImportDraft.model_validate(parsed)
