# Biblioteca de Blocos de Sabor do Nordeste — Fernando

Versão **0.2.0**. Fonte canônica dos dados do **Laje Signature**.

## Conteúdo

- 100 ingredientes
- 100 blocos de sabor **atômicos** (1 ingrediente = 1 bloco)
- 20 protagonistas · 20 bases · 20 acidez · 20 texturas
- 15 famílias aromáticas
- 25 regras de compatibilidade · 20 conflitos
- 30 substituições regionais · 100 registros de sazonalidade

## Layout

```
library/
├── library.json          # snapshot runtime
├── library.yaml
├── loader.py
├── validation_report.json
├── SOURCES.md
├── catalog/              # YAMLs editáveis por coleção
├── schemas/models.py
└── examples/
```

Documentação detalhada: [`../../docs/DATA.md`](../../docs/DATA.md).

## Uso rápido

```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path("data/library").resolve()))
from loader import load_library, by_id

lib = load_library()
blocks = by_id(lib["flavor_blocks"])
```

No app, prefira `app.composition.library_v01.load_library()`.

## Filosofia

Cada **bloco é atômico** (um ingrediente / conceito).  
O prato nasce da **composição** de vários blocos com funções claras: protagonista, base, molho, acidez, textura, aroma.  
Preferir poucos blocos bem escolhidos a combinações pré-montadas.
