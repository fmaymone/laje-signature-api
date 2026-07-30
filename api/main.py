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

from api.routes import (  # noqa: E402
    auth,
    blocks,
    compose,
    compose_graphs,
    health,
    library,
    recipes,
    users,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    import os

    from alembic import command
    from alembic.config import Config

    from app.composition.library_v01 import load_library
    from app.db.config import get_database_url

    # Em testes usamos create_all; em runtime migramos via Alembic.
    if os.getenv("SKIP_DB_MIGRATE", "").lower() not in {"1", "true", "yes"}:
        alembic_cfg = Config(str(_ROOT / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", get_database_url())
        command.upgrade(alembic_cfg, "head")

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
        "https://laje-signature-web.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(library.router)
app.include_router(blocks.router)
app.include_router(compose.router)
app.include_router(compose_graphs.router)
app.include_router(recipes.router)
app.include_router(users.router)


@app.get("/")
def root() -> dict:
    return {
        "name": "Laje Signature API",
        "docs": "/docs",
        "health": "/health",
    }
