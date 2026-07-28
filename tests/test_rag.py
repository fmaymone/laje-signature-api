"""Testes leves da Fase 2 (RAG) — sem chamar a API de embeddings."""

from app.rag import format_search_results, knowledge_paths, load_knowledge_documents
from langchain_core.documents import Document


def test_knowledge_corpus_is_present():
    paths = knowledge_paths()
    assert paths, "Esperado ao menos uma ficha em knowledge/"
    assert any("recipes" in p.as_posix() for p in paths)


def test_load_knowledge_documents_has_metadata():
    docs = load_knowledge_documents()
    assert len(docs) >= 4
    for doc in docs:
        assert doc.page_content
        assert "source" in doc.metadata
        assert "category" in doc.metadata


def test_format_search_results_empty():
    assert "Nenhum trecho" in format_search_results([])


def test_format_search_results_with_docs():
    docs = [
        Document(
            page_content="Sirigado na brasa.",
            metadata={"source": "recipes/x.md", "category": "recipes"},
        )
    ]
    text = format_search_results(docs)
    assert "recipes/x.md" in text
    assert "Sirigado" in text
