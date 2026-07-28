"""Diagnóstico: pedido 'Quero um prato com lagosta'."""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")


def main() -> None:
    t0 = time.time()
    print("1) parse...", flush=True)
    from app.request_parser import parse_cooking_request

    t = time.time()
    req = parse_cooking_request("Quero um prato com lagosta")
    print(f"   parse ok in {time.time() - t:.1f}s: {req.model_dump()}", flush=True)

    print("2) deterministic compose...", flush=True)
    from app.composition import compose_from_library_v01

    t = time.time()
    resolved, _arch = compose_from_library_v01(
        mentions=req.ingredients + [req.objective] + req.equipment,
        equipment=req.equipment,
    )
    print(
        f"   compose ok in {time.time() - t:.1f}s "
        f"blocks={[b['id'] for b in resolved['selected_blocks']]}",
        flush=True,
    )

    print("3) retrieve_context (RAG/embeddings)...", flush=True)
    from app.nodes import retrieve_context

    t = time.time()
    try:
        ctx = retrieve_context({"request": req})
        print(
            f"   retrieve ok in {time.time() - t:.1f}s "
            f"recipes={len(ctx.get('relevant_recipes', []))}",
            flush=True,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"   retrieve FAILED in {time.time() - t:.1f}s: {exc}", flush=True)

    print("4) full graph (max_revisions=1)...", flush=True)
    from app.graph import culinary_graph

    t = time.time()
    try:
        result = culinary_graph.invoke(
            {
                "request": req,
                "relevant_memories": ["Prefere poucos componentes."],
                "revision_count": 0,
                "max_revisions": 1,
            }
        )
        print(f"   graph ok in {time.time() - t:.1f}s", flush=True)
        final = result["final_recipe"]
        review = result.get("fernando_review")
        print(f"TITLE: {final.title}", flush=True)
        print(f"COMPONENTS: {[c.name for c in final.components]}", flush=True)
        print(
            f"SCORE: {getattr(review, 'score', None)} "
            f"approved={getattr(review, 'approved', None)}",
            flush=True,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"   FAILED after {time.time() - t:.1f}s: {exc}", flush=True)
        traceback.print_exc()

    print(f"TOTAL {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
