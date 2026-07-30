# Laje Signature

Motor de **alta culinária nordestina** do restaurante **Laje**: composição por blocos de sabor, regras determinísticas e geração de pratos assinatura — CLI + API FastAPI.

Não é um “chat que inventa receitas”. O centro é uma **biblioteca de dados versionada** + um grafo que compõe, equilibra e só então pede ao LLM para escrever a execução.

## Destaques

- Biblioteca Fernando Nordeste **v0.2.0** — 100 ingredientes, 100 blocos atômicos, regras de compatibilidade/conflito
- Composição determinística (código) + escrita/revisão (LLM)
- API REST + SSE para apps
- RAG auxiliar sobre fichas técnicas em `knowledge/`

## Estrutura do repositório

```
laje-signature-api/
├── api/                 # FastAPI (HTTP)
├── app/
│   ├── db/              # SQLAlchemy models + sessão
│   ├── composition/     # blocos de sabor
│   └── ...
├── alembic/             # migrações
├── data/library/        # biblioteca canônica de sabor
├── docker-compose.yml   # Postgres local
├── docs/
├── knowledge/
├── scripts/
├── tests/
└── main.py
```

## Início rápido

```bash
cd laje-signature-api
cp .env.example .env
# OPENAI_API_KEY=...
# DATABASE_URL=... (SQLite local ou Postgres)

uv sync

# Banco (migrações)
uv run alembic upgrade head

# CLI interativo
uv run python -m app.cli

# API
uv run uvicorn api.main:app --reload --port 8000
# Docs: http://localhost:8000/docs

# Produção (Render): https://laje-signature-api.onrender.com
```

### Banco de dados

- ORM: SQLAlchemy 2 + Alembic  
- Local rápido: SQLite (`laje_signature.db`)  
- Recomendado: Postgres via Docker:

```bash
docker compose up -d
# DATABASE_URL=postgresql+psycopg://laje:laje@localhost:5432/laje_signature
uv run alembic upgrade head
```

Entidade inicial: **`users`** (`app/db/models/user.py`).

## Dados

A fonte da verdade é [`data/library/`](data/library/).

| Arquivo / pasta | Conteúdo |
|-----------------|----------|
| `library.json` / `library.yaml` | Snapshot único carregado em runtime |
| `catalog/*.yaml` | Coleções editáveis (ingredientes, blocos, regras…) |
| `SOURCES.md` | Referências (Embrapa, Fundaj, defesos…) |
| `validation_report.json` | Contagens e validação de IDs |

Documentação completa: **[docs/DATA.md](docs/DATA.md)**.

## Fluxo do grafo

```
Pedido
  → retrieve (perfil + RAG)
  → regional (substituições)
  → select_blocks
  → complete_catalogs   # bases, acidez, texturas, aromas, sazonalidade
  → compatibility_rules
  → conflict_rules
  → write (LLM)
  → technical ⇄ write
  → critic Fernando ⇄ select_blocks
  → finalizer
```

## API (resumo)

| Método | Endpoint | Uso |
|--------|----------|-----|
| GET | `/health` | Saúde (biblioteca + DB) |
| GET | `/v1/library/summary` | Contagens |
| GET | `/v1/library/{collection}` | Catálogo (`?q=`) |
| POST | `/v1/compose/preview` | Preview sem LLM |
| POST | `/v1/chat/parse` | Texto → pedido |
| POST | `/v1/recipes/generate` | Receita síncrona |
| POST | `/v1/recipes/generate/stream` | SSE com etapas |
| POST | `/v1/users` | Criar usuário |
| GET | `/v1/users` | Listar usuários |
| GET | `/v1/users/{id}` | Detalhe |
| PATCH | `/v1/users/{id}` | Atualizar |

## Filosofia

1. Protagonista → base → molho → acidez → textura → aroma  
2. Preferir componentes multifunção; ~4–6 no máximo  
3. Técnica só quando gera benefício sensorial perceptível  
4. Identidade nordestina por **função**, não por folclore

## Licença e contribuição

Dados e código destinam-se ao atelier Laje.  
Ao editar a biblioteca: altere `catalog/*.yaml`, regenere `library.json` se necessário, rode os testes e atualize `validation_report.json`.
