"""RAG sobre fichas técnicas, ingredientes, técnicas e equipamentos."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

_KNOWLEDGE_ROOT = Path(__file__).resolve().parent.parent / "knowledge"
_CORPUS_DIRS = (
    "recipes",
    "ingredients",
    "techniques",
    "equipment",
)
_EXTENSIONS = {".md", ".markdown", ".txt", ".yaml", ".yml"}


def knowledge_paths() -> list[Path]:
    paths: list[Path] = []
    for dirname in _CORPUS_DIRS:
        directory = _KNOWLEDGE_ROOT / dirname
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.suffix.lower() in _EXTENSIONS:
                if path.name == ".gitkeep":
                    continue
                paths.append(path)
    return paths


def _infer_region(path: Path, text: str) -> str | None:
    relative = path.relative_to(_KNOWLEDGE_ROOT).as_posix().lower()
    if "ceara" in relative or "ceará" in text.lower() or "cearense" in text.lower():
        return "ceara"
    match = re.search(r"\*\*Regi[aã]o:\*\*\s*([^\n]+)", text, re.IGNORECASE)
    if match:
        value = match.group(1).strip().lower()
        if "cear" in value:
            return "ceara"
        return value
    return None


def _infer_tags(text: str) -> list[str]:
    match = re.search(r"\*\*Tags:\*\*\s*([^\n]+)", text, re.IGNORECASE)
    if not match:
        return []
    return [tag.strip().lower() for tag in match.group(1).split(",") if tag.strip()]


def load_knowledge_documents() -> list[Document]:
    documents: list[Document] = []
    for path in knowledge_paths():
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        relative = path.relative_to(_KNOWLEDGE_ROOT).as_posix()
        # categoria = primeiro segmento (recipes, ingredients, ...)
        category = relative.split("/", 1)[0]
        region = _infer_region(path, text)
        tags = _infer_tags(text)
        metadata = {
            "source": relative,
            "category": category,
            "title": path.stem.replace("-", " "),
            "tags": ", ".join(tags),
        }
        if region:
            metadata["region"] = region
        documents.append(Document(page_content=text, metadata=metadata))
    return documents


def _split_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=150,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    return splitter.split_documents(documents)


@lru_cache(maxsize=1)
def get_recipe_store() -> InMemoryVectorStore:
    """Indexa o corpus em memória. Requer OPENAI_API_KEY para embeddings."""
    documents = load_knowledge_documents()
    if not documents:
        raise FileNotFoundError(
            "Nenhuma ficha encontrada em knowledge/. "
            "Adicione arquivos em recipes|ingredients|techniques|equipment."
        )

    chunks = _split_documents(documents)
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
    )
    return InMemoryVectorStore.from_documents(chunks, embedding=embeddings)


def search_knowledge(
    query: str,
    k: int = 4,
    *,
    region: str | None = None,
    category: str | None = None,
) -> list[Document]:
    store = get_recipe_store()
    fetch_k = max(k * 4, 12) if (region or category) else k
    documents = store.similarity_search(query, k=fetch_k)

    if region:
        region_norm = region.lower()
        documents = [
            doc
            for doc in documents
            if doc.metadata.get("region", "").lower() == region_norm
            or region_norm in doc.metadata.get("source", "").lower()
            or region_norm in doc.page_content.lower()
        ]

    if category:
        category_norm = category.lower()
        documents = [
            doc
            for doc in documents
            if doc.metadata.get("category", "").lower() == category_norm
        ]

    return documents[:k]


def search_ceara_knowledge(query: str, k: int = 5) -> list[Document]:
    """Atalho: prioriza corpus cearense (fichas + catálogo de ingredientes)."""
    enriched = f"Ceará cearense {query}"
    return search_knowledge(enriched, k=k, region="ceara")


def format_search_results(documents: list[Document]) -> str:
    if not documents:
        return "Nenhum trecho relevante encontrado nas fichas técnicas."

    parts: list[str] = []
    for i, doc in enumerate(documents, start=1):
        source = doc.metadata.get("source", "desconhecido")
        category = doc.metadata.get("category", "")
        region = doc.metadata.get("region")
        region_bit = f" | {region}" if region else ""
        header = f"[{i}] ({category}{region_bit}) {source}"
        parts.append(f"{header}\n{doc.page_content.strip()}")
    return "\n\n---\n\n".join(parts)


def reset_recipe_store() -> None:
    """Invalida o índice em memória (útil após adicionar fichas)."""
    get_recipe_store.cache_clear()
