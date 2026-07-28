from pathlib import Path
import json

def load_library(path: str | Path = Path(__file__).with_name("library.json")) -> dict:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def by_id(items: list[dict]) -> dict[str, dict]:
    return {item["id"]: item for item in items}

if __name__ == "__main__":
    lib = load_library()
    print({k: len(v) for k, v in lib.items() if isinstance(v, list)})
