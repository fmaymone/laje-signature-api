"""Entrypoint — demo única ou chat interativo.

  python main.py          # pedido fixo de exemplo
  python main.py --chat   # chat interativo
  python -m app.cli       # chat interativo
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT.parent / ".env")


def run_demo() -> None:
    from app.graph import culinary_graph
    from app.schemas import CookingRequest

    request = CookingRequest(
        objective=(
            "Prato principal nordestino contemporâneo com sirigado e milho. "
            "Usar churrasqueira e TM7."
        ),
        ingredients=[
            "1,5 kg de sirigado",
            "6 espigas de milho",
            "manteiga de garrafa",
            "limão",
            "coentro",
            "castanha de caju",
        ],
        servings=6,
        equipment=[
            "Thermomix TM7",
            "churrasqueira",
            "forno Elettromec sem vapor",
        ],
    )

    result = culinary_graph.invoke(
        {
            "request": request,
            "relevant_memories": [
                "Prefere levar peixes firmes à churrasqueira.",
                "Gosta de usar aparas para produzir caldo ou glace.",
                "Prefere poucos componentes com função clara.",
            ],
            "revision_count": 0,
            "max_revisions": 2,
        }
    )

    architecture = result.get("architecture")
    sensory = result.get("sensory_report")
    blocks = result.get("conflict_result") or result.get("block_selection")
    review = result.get("fernando_review")
    final = result["final_recipe"]

    print("=== BLOCOS (v0.1) ===")
    if blocks:
        selected = blocks.get("selected_blocks", [])
        print([b.get("id") for b in selected])
        print(
            "compat:",
            [r.get("id") for r in blocks.get("compatibility_triggered", [])],
        )
        print(
            "conflict:",
            [r.get("id") for r in blocks.get("conflicts_triggered", [])],
        )
    print()
    print("=== ARQUITETURA ===")
    if architecture:
        print(architecture.model_dump_json(indent=2))
    print()
    if sensory:
        print("=== SENSORIAL ===")
        print(sensory.model_dump_json(indent=2))
        print()
    print(
        f"# Revisões crítico: {result.get('revision_count', 0)} | "
        f"score={getattr(review, 'score', None)} | "
        f"aprovado={getattr(review, 'approved', None)}"
    )
    print()
    print("=== RECEITA FINAL ===")
    print(final.model_dump_json(indent=2))


def main() -> None:
    if "--chat" in sys.argv or "-c" in sys.argv:
        from app.cli import chat_loop

        chat_loop()
        return
    run_demo()


if __name__ == "__main__":
    main()
