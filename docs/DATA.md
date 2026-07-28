# Dados — Laje Signature / Biblioteca Nordeste v0.1.0

Este documento descreve os datasets em [`../data/library/`](../data/library/).

## Visão geral

| Coleção | Qtd | Arquivo | Papel |
|---------|-----|---------|--------|
| `ingredients` | 100 | `catalog/ingredients.yaml` | Ingredientes nordestinos + perfil sensorial |
| `flavor_blocks` | 50 | `catalog/flavor_blocks.yaml` | Combinações prontas (núcleo do compositor) |
| `protagonists` | 20 | `catalog/protagonists.yaml` | Proteínas/vegetais principais + guardrails |
| `bases` | 20 | `catalog/bases.yaml` | Purês, cremes, cuscuz, xerém… |
| `acidity_sources` | 20 | `catalog/acidity_sources.yaml` | Limão, caju, umbu, vinagres… |
| `textures` | 20 | `catalog/textures.yaml` | Farofas, chips, tostados… |
| `aromatic_families` | 15 | `catalog/aromatic_families.yaml` | Famílias de aroma/finalização |
| `compatibility_rules` | 25 | `catalog/compatibility_rules.yaml` | Regras “se X então equilibrar Y” |
| `conflict_rules` | 20 | `catalog/conflict_rules.yaml` | Combinações a evitar / resolver |
| `regional_substitutions` | 30 | `catalog/regional_substitutions.yaml` | Parmesão→coalho, batata→macaxeira… |
| `seasonality` | 100 | `catalog/seasonality.yaml` | Picos, disponibilidade, alertas de defeso |

Runtime carrega o snapshot agregado:

- `library.json` (preferido pelo loader)
- `library.yaml` (legível para diff/review)

## O que é um bloco de sabor

Um **bloco** não é um ingrediente isolado. É um conjunto de ingredientes + papéis culinários + perfil sensorial alvo + texturas.

Exemplo (`sirigado_milho_e_brasa`):

- ingredientes: sirigado, milho verde, manteiga de garrafa, limão-cravo  
- papéis: protagonista, base, brasa, acidez  
- texturas alvo: firme, cremoso, tostado  

O compositor escolhe blocos compatíveis com o protagonista e completa lacunas com `bases`, `acidity_sources`, `textures` e `aromatic_families`.

## Escala sensorial

Campos típicos (0–10, heurísticos):

`acidity`, `saltiness`, `sweetness`, `bitterness`, `umami`, `fat`, `heat`, `aroma`, `freshness`

Devem ser calibrados por quantidade, maturação e técnica. Não são medidas laboratoriais.

## Definição de “nordestino”

Inclui itens **nativos, tradicionais, costeiros** ou **amplamente cultivados/encontrados** na região.  
Referências e critérios: [`../data/library/SOURCES.md`](../data/library/SOURCES.md).

## Sazonalidade e pescados

- `peak_months`: janela indicativa (1–12), não garantia  
- `confidence`: confiança da janela  
- `legal_restriction`: alerta operacional (ex.: defeso) — **sempre verificar norma vigente na compra**

## Como o código usa os dados

```
select_blocks          ← flavor_blocks + protagonists
complete_catalogs      ← bases, acidity_sources, textures, aromatic_families, seasonality
apply_compatibility    ← compatibility_rules
apply_conflicts        ← conflict_rules
regional               ← regional_substitutions + ingredients
```

API de leitura: `GET /v1/library/{collection}`.

## Como editar com segurança

1. Edite o YAML em `data/library/catalog/`  
2. Atualize `library.json` / `library.yaml` (snapshot) para o runtime refletir a mudança  
3. Rode:

```bash
uv run pytest tests/test_library_v01.py tests/test_api.py -q
```

4. Não altere IDs referenciados por blocos sem atualizar as referências cruzadas (`validation_report.json` ajuda a checar)

## Knowledge operacional (fora da biblioteca)

Em [`../knowledge/`](../knowledge/):

| Pasta | Uso |
|-------|-----|
| `chef_profile.yaml` | Identidade culinária versionada (somente leitura pelo agente) |
| `recipes/` | Fichas técnicas para RAG |
| `techniques/`, `equipment/` | Corpus RAG complementar |
| `ingredients/` | Notas regionais auxiliares (ex.: Ceará) |
| `_archive/` | Protótipos antigos (não canônicos) |

## Versionamento

- Versão atual da biblioteca: **0.1.0** (`metadata.version`)  
- Mudanças de schema ou rebalanceamento sensorial devem subir o minor/major e ser documentadas neste arquivo
