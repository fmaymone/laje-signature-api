"""Testes do corpus RAG cearense — sem chamar a API de embeddings."""

from app.rag import (
    knowledge_paths,
    load_knowledge_documents,
    _infer_region,
)
from pathlib import Path


def test_ceara_ingredient_catalog_is_indexed():
    paths = knowledge_paths()
    assert any("ingredients/ceara.yaml" in p.as_posix().replace("\\", "/") for p in paths)


def test_ceara_recipes_are_present():
    paths = knowledge_paths()
    ceara_recipes = [
        p for p in paths if "recipes/ceara" in p.as_posix().replace("\\", "/")
    ]
    assert len(ceara_recipes) >= 5


def test_ceara_documents_have_region_metadata():
    docs = load_knowledge_documents()
    ceara_docs = [d for d in docs if d.metadata.get("region") == "ceara"]
    assert len(ceara_docs) >= 6


def test_infer_region_from_path():
    fake = Path("knowledge/recipes/ceara/x.md")
    # Use a real path from corpus
    paths = knowledge_paths()
    ceara_path = next(p for p in paths if "ceara" in p.as_posix().lower())
    text = ceara_path.read_text(encoding="utf-8")
    assert _infer_region(ceara_path, text) == "ceara"
