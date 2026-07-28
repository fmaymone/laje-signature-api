"""Chat interativo com o motor de composição nordestina."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT.parent / ".env")

from app.graph import culinary_graph
from app.request_parser import parse_cooking_request
from app.schemas import CookingRequest, FinalRecipe


HELP = """
Comandos:
  /ajuda              mostra esta ajuda
  /memoria <texto>    adiciona preferência à sessão
  /memorias           lista memórias da sessão
  /limpar             limpa memórias da sessão
  /pedido             mostra o último CookingRequest parseado
  /sair               encerra o chat

Ou digite um pedido livre, por exemplo:
  Tenho 1,5 kg de sirigado e milho para 6 pessoas, churrasqueira e TM7.
  Carne de sol com banana da terra, sem farofa, para 4.
""".strip()


def _print_recipe(final: FinalRecipe, meta: dict) -> None:
    print()
    print("=" * 60)
    print(final.title)
    print("=" * 60)
    print(final.concept)
    print()
    print(f"Porções: {final.servings}")
    print(f"Equipamentos: {', '.join(final.equipment)}")
    if meta.get("blocks"):
        print(f"Blocos: {', '.join(meta['blocks'])}")
    if meta.get("catalog_picks"):
        picks = [
            f"{p.get('catalog')}:{p.get('id')}" for p in meta["catalog_picks"]
        ]
        print(f"Catálogos: {', '.join(picks)}")
    if meta.get("seasonality_notes"):
        print("Sazonalidade:")
        for note in meta["seasonality_notes"]:
            print(f"  · {note}")
    if meta.get("score") is not None:
        print(
            f"Crítico Fernando: score={meta['score']} | "
            f"aprovado={meta.get('approved')} | "
            f"revisões={meta.get('revisions')}"
        )
    if final.revision_warning:
        print(f"Aviso: {final.revision_warning}")
    print()

    for component in final.components:
        print(f"## {component.name}")
        print(f"Função: {component.purpose}")
        print("Ingredientes:")
        for item in component.ingredients:
            print(f"  - {item}")
        print("Preparo:")
        for i, step in enumerate(component.instructions, start=1):
            print(f"  {i}. {step}")
        if component.critical_points:
            print("Pontos críticos:")
            for point in component.critical_points:
                print(f"  ! {point}")
        print()

    if final.timeline:
        print("## Cronograma")
        for item in final.timeline:
            print(f"  - {item}")
        print()

    if final.plating:
        print("## Montagem")
        for item in final.plating:
            print(f"  - {item}")
        print()

    if final.why_this_matches_fernando:
        print("## Por que parece Fernando")
        for item in final.why_this_matches_fernando:
            print(f"  - {item}")
        print()


def run_recipe(
    request: CookingRequest,
    memories: list[str],
    max_revisions: int = 1,
) -> tuple[FinalRecipe, dict]:
    labels = {
        "retrieve": "contexto / RAG",
        "regional": "substituições regionais",
        "select_blocks": "blocos de sabor",
        "complete_catalogs": "bases / acidez / textura / aroma",
        "apply_compatibility": "regras de compatibilidade",
        "apply_conflicts": "regras de conflito",
        "write": "escrevendo receita (LLM)…",
        "technical": "revisão técnica (LLM)…",
        "critic": "crítico Fernando (LLM)…",
        "finalizer": "finalizando",
    }

    if not request.equipment:
        request = request.model_copy(
            update={
                "equipment": ["Thermomix TM7", "churrasqueira"],
            }
        )

    payload = {
        "request": request,
        "relevant_memories": list(memories),
        "revision_count": 0,
        "max_revisions": max_revisions,
    }

    state: dict = dict(payload)
    for event in culinary_graph.stream(payload, stream_mode="updates"):
        for node_name, update in event.items():
            print(f"  · {labels.get(node_name, node_name)}", flush=True)
            if isinstance(update, dict):
                state.update(update)

    final = state["final_recipe"]
    blocks_state = state.get("conflict_result") or state.get("block_selection") or {}
    block_ids = [
        block.get("id")
        for block in blocks_state.get("selected_blocks", [])
        if isinstance(block, dict)
    ]
    review = state.get("fernando_review")
    meta = {
        "blocks": block_ids,
        "catalog_picks": blocks_state.get("catalog_picks", []),
        "seasonality_notes": blocks_state.get("seasonality_notes", [])[:5],
        "score": getattr(review, "score", None),
        "approved": getattr(review, "approved", None),
        "revisions": state.get("revision_count", 0),
    }
    return final, meta


def chat_loop() -> None:
    memories: list[str] = [
        "Prefere poucos componentes com função clara.",
        "Valoriza brasa, fundos e acidez clara.",
    ]
    last_request: CookingRequest | None = None

    print("Laje Signature — chat interativo (Nordeste v0.1)")
    print("Digite /ajuda para comandos. Ctrl+C também sai.\n")

    while True:
        try:
            raw = input("você> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté logo.")
            break

        if not raw:
            continue

        lower = raw.lower()
        if lower in {"/sair", "/exit", "/quit", "sair", "exit"}:
            print("Até logo.")
            break

        if lower in {"/ajuda", "/help", "ajuda"}:
            print(HELP)
            continue

        if lower.startswith("/memoria "):
            note = raw.split(" ", 1)[1].strip()
            if note:
                memories.append(note)
                print(f"Memória adicionada ({len(memories)}).")
            continue

        if lower in {"/memorias", "/memoria"}:
            if not memories:
                print("Nenhuma memória na sessão.")
            else:
                for i, memory in enumerate(memories, start=1):
                    print(f"  {i}. {memory}")
            continue

        if lower == "/limpar":
            memories.clear()
            print("Memórias limpas.")
            continue

        if lower == "/pedido":
            if last_request is None:
                print("Nenhum pedido ainda.")
            else:
                print(last_request.model_dump_json(indent=2))
            continue

        print("Interpretando pedido…")
        try:
            request = parse_cooking_request(raw)
        except Exception as exc:  # noqa: BLE001
            print(f"Não consegui interpretar: {exc}")
            continue

        last_request = request
        print(
            f"Pedido: {request.objective} | "
            f"{request.servings} porções | "
            f"ingredientes={request.ingredients} | "
            f"equipamentos={request.equipment}"
        )
        print("Compondo… (etapas aparecem abaixo; LLM pode levar 1–2 min cada)")
        print()

        try:
            final, meta = run_recipe(request, memories)
        except Exception as exc:  # noqa: BLE001
            print(f"Falha ao gerar receita: {exc}")
            continue

        _print_recipe(final, meta)
        print("Pronto. Faça outro pedido ou /sair.\n")


def main() -> None:
    chat_loop()


if __name__ == "__main__":
    main()
