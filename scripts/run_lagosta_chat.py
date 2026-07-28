"""Roda o pedido de lagosta com progresso (como o chat)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")

from app.cli import run_recipe
from app.request_parser import parse_cooking_request


def main() -> None:
    t0 = time.time()
    print("Interpretando…", flush=True)
    request = parse_cooking_request("Quero um prato com lagosta")
    print(request.model_dump_json(indent=2), flush=True)
    print("Compondo…", flush=True)
    final, meta = run_recipe(
        request,
        memories=["Prefere poucos componentes com função clara."],
        max_revisions=1,
    )
    print()
    print("TITLE:", final.title, flush=True)
    print("BLOCKS:", meta["blocks"], flush=True)
    print("CATALOGS:", meta["catalog_picks"], flush=True)
    print("SCORE:", meta["score"], "approved=", meta["approved"], flush=True)
    print("COMPONENTS:", [c.name for c in final.components], flush=True)
    print(f"TOTAL {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
