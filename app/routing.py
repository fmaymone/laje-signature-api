from typing import Literal

from app.state import CulinaryState


def after_technical_review(
    state: CulinaryState,
) -> Literal["critic", "revise"]:
    review = state["technical_review"]

    if review.approved:
        return "critic"

    # Evita loop infinito se o técnico continuar reprovando
    technical_revisions = state.get("technical_revision_count", 0)
    maximum = state.get("max_revisions", 3)
    if technical_revisions >= maximum:
        return "critic"

    return "revise"


def after_fernando_review(
    state: CulinaryState,
) -> Literal["finalize", "revise", "finalize_with_warning"]:
    review = state["fernando_review"]
    revisions = state.get("revision_count", 0)
    maximum = state.get("max_revisions", 3)

    if review.approved and review.score >= 8:
        return "finalize"

    if revisions < maximum:
        return "revise"

    return "finalize_with_warning"
