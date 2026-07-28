"""Compat: redireciona para o workflow multiagente."""

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT.parent / ".env")

from main import main

if __name__ == "__main__":
    main()
