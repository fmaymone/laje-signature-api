"""Parser vision: print de receita → RecipeImageImportDraft (transcrição fiel)."""

from __future__ import annotations

import base64
from functools import lru_cache

from langchain.agents import create_agent

from api.schemas_recipe_import import RecipeImageImportDraft
from app.agents import get_model

RECIPE_IMAGE_PARSER_PROMPT = """
Você transcreve receitas a partir de imagens (prints, fotos de caderno, screenshots).

Regras absolutas:
- Extraia APENAS o que está legível na imagem. Não invente ingredientes, passos,
  tempos, porções ou técnicas que não apareçam.
- Idioma de saída: SEMPRE português do Brasil.
  Se o texto da imagem estiver em inglês (ou outro idioma), traduza title, notes,
  nomes de ingredientes, process, description e avisos para português.
  Preserve o sentido e as quantidades; não reinterpretar a receita.
  Se já estiver em português, mantenha como está (só normalize ortografia óbvia).
  Em warnings, inclua uma linha quando houver tradução (ex.: "Traduzido do inglês").
- Se algo estiver ilegível ou ambíguo, omita ou use o campo warnings.
- title: nome do prato/receita se houver; senão um título curto descritivo do que
  está na imagem (ex.: "Receita sem título").
- notes: observações gerais da receita se houver; senão null.
- servings: número de porções se indicado; senão 4.
- ingredients: cada linha com name, quantity (número; 0 se só "a gosto"),
  unit e notes opcional. Nomes de ingredientes em português
  (ex.: shrimp → camarão; garlic → alho; onion → cebola).
  Unidades permitidas (mapeie o mais próximo):
  g, kg, ml, l, un, xicara, colher_sopa, colher_cha, dente, folha, ramo, a_gosto.
  Exemplos: cup → xicara; tbsp/tablespoon → colher_sopa; tsp/teaspoon → colher_cha;
  "xícara"/"xíc." → xicara; "colher de sopa"/"cs" → colher_sopa;
  "colher de chá"/"cc" → colher_cha; piece/unit → un; to taste → a_gosto.
- steps: processo curto em `process` (verbo/ação em português) e detalhe em
  `description` (português). Gere ids curtos únicos (s1, s2, …).
  `process` é a ação do passo (refogar, temperar), não o nome da seção.
  time_before_service_minutes e duration_minutes só se estiverem na imagem;
  senão use duration_minutes=10 e time_before_service_minutes=0.
- lanes: se houver componentes/seções (ensopado, molho, guarnição) ou linhas
  paralelas, crie uma lane por componente e use lane_id nos passos.
  Senão use [{id:"main", name:"Principal"}].
- warnings: liste ambiguidades (unidade pouco clara, texto cortado, etc.) em português.

Responda no schema solicitado. Não reinterpretar o estilo culinário.
""".strip()


@lru_cache(maxsize=1)
def get_recipe_image_parser_agent():
    return create_agent(
        model=get_model(),
        system_prompt=RECIPE_IMAGE_PARSER_PROMPT,
        response_format=RecipeImageImportDraft,
    )


def parse_recipe_from_image(*, image_bytes: bytes, mime_type: str) -> RecipeImageImportDraft:
    if not image_bytes:
        raise ValueError("Imagem vazia.")
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{b64}"
    result = get_recipe_image_parser_agent().invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Transcreva fielmente a receita desta imagem "
                                "para o schema solicitado. Se estiver em inglês "
                                "ou outro idioma, traduza tudo para português do Brasil."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                    ],
                }
            ]
        }
    )
    parsed = result.get("structured_response")
    if parsed is None:
        raise ValueError("Não foi possível ler a receita na imagem.")
    if isinstance(parsed, RecipeImageImportDraft):
        return parsed
    return RecipeImageImportDraft.model_validate(parsed)
