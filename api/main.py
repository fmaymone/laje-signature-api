"""FastAPI entrypoint — Laje Signature API."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT.parent / ".env")

from api.routes import compose, health, library, recipes  # noqa: E402


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Pré-carrega a biblioteca na subida
    from app.composition.library_v01 import load_library

    load_library()
    yield


app = FastAPI(
    title="Laje Signature API",
    description=(
        "API do atelier Laje: biblioteca nordestina e motor de "
        "composição de pratos assinatura (LangGraph + blocos de sabor)."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(library.router)
app.include_router(compose.router)
app.include_router(recipes.router)


@app.get("/")
def root() -> dict:
    return {
        "name": "Laje Signature API",
        "docs": "/docs",
        "health": "/health",
    }
