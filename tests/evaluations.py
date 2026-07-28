"""Avaliações do crítico culinário — Fase 4 (stub).

Critérios planejados:
- coerência com o perfil Fernando
- complexidade justificada
- equilíbrio sabor/textura
- uso realista dos equipamentos
- fidelidade às preferências aprendidas por feedback
"""


def evaluate_against_profile(plan: dict, profile: dict) -> dict:
    """Placeholder: retorna checklist vazio até a Fase 4."""
    return {
        "score": None,
        "checks": [],
        "rejected": False,
        "notes": [
            "Avaliação automática ainda não implementada. "
            "Use feedback manual pós-receita para alimentar a memória longa."
        ],
        "profile_name": profile.get("name"),
        "plan_title": plan.get("title"),
    }
