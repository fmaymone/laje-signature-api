# Laje Signature

Motor de **alta culinária nordestina** do restaurante **Laje**: composição por blocos de sabor, regras determinísticas e geração de pratos assinatura — CLI + API FastAPI.

Não é um “chat que inventa receitas”. O centro é uma **biblioteca de dados versionada** + um grafo que compõe, equilibra e só então pede ao LLM para escrever a execução.

## Destaques

- Biblioteca Fernando Nordeste **v0.1.0** — 100 ingredientes, 50 blocos, regras de compatibilidade/conflito
- Composição determinística (código) + escrita/revisão (LLM)
- API REST + SSE para apps
- RAG auxiliar sobre fichas técnicas em `knowledge/`

## Estrutura do repositório

```
laje-signature/
├── api/                 # FastAPI (consumo pelo app)
├── app/                 # Domínio: grafo, composição, CLI
├── data/
│   └── library/         # ★ Biblioteca canônica de sabor (dados)
├── docs/
│   └── DATA.md          # Dicionário dos datasets
├── knowledge/           # Perfil do chef + RAG (receitas/técnicas)
├── scripts/             # Utilitários / diagnóstico
├── tests/
├── main.py              # Demo / --chat
└── requirements.txt
```

## Início rápido

```bash
cd laje-signature
cp .env.example .env
# OPENAI_API_KEY=...

uv sync

# CLI interativo
uv run python -m app.cli

# API
uv run uvicorn api.main:app --reload --port 8000
# Docs: http://localhost:8000/docs
```

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
| GET | `/health` | Saúde |
| GET | `/v1/library/summary` | Contagens |
| GET | `/v1/library/{collection}` | Catálogo (`?q=`) |
| POST | `/v1/compose/preview` | Preview sem LLM |
| POST | `/v1/chat/parse` | Texto → pedido |
| POST | `/v1/recipes/generate` | Receita síncrona |
| POST | `/v1/recipes/generate/stream` | SSE com etapas |

## Filosofia

1. Protagonista → base → molho → acidez → textura → aroma  
2. Preferir componentes multifunção; ~4–6 no máximo  
3. Técnica só quando gera benefício sensorial perceptível  
4. Identidade nordestina por **função**, não por folclore

## Licença e contribuição

Dados e código destinam-se ao atelier Laje.  
Ao editar a biblioteca: altere `catalog/*.yaml`, regenere `library.json` se necessário, rode os testes e atualize `validation_report.json`.
