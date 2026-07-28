from app.routing import after_fernando_review, after_technical_review
from app.schemas import FernandoReview, TechnicalReview


def test_technical_approved_goes_to_critic():
    state = {
        "technical_review": TechnicalReview(
            approved=True,
            problems=[],
            required_changes=[],
            timing_notes=[],
            safety_notes=[],
        ),
        "technical_revision_count": 0,
        "max_revisions": 3,
    }
    assert after_technical_review(state) == "critic"


def test_technical_rejected_revises():
    state = {
        "technical_review": TechnicalReview(
            approved=False,
            problems=["tempo vago"],
            required_changes=["definir temperatura"],
            timing_notes=[],
            safety_notes=[],
        ),
        "technical_revision_count": 1,
        "max_revisions": 3,
    }
    assert after_technical_review(state) == "revise"


def test_technical_exhausted_forces_critic():
    state = {
        "technical_review": TechnicalReview(
            approved=False,
            problems=["ainda vago"],
            required_changes=[],
            timing_notes=[],
            safety_notes=[],
        ),
        "technical_revision_count": 3,
        "max_revisions": 3,
    }
    assert after_technical_review(state) == "critic"


def test_fernando_high_score_finalizes():
    state = {
        "fernando_review": FernandoReview(
            approved=True,
            score=8.5,
            feels_like_fernando=True,
            strengths=["brasa"],
            problems=[],
            required_changes=[],
            unnecessary_complexity=[],
            missing_contrasts=[],
        ),
        "revision_count": 1,
        "max_revisions": 3,
    }
    assert after_fernando_review(state) == "finalize"


def test_fernando_reject_revises_when_budget():
    state = {
        "fernando_review": FernandoReview(
            approved=False,
            score=6.0,
            feels_like_fernando=False,
            strengths=[],
            problems=["espuma"],
            required_changes=["remover espuma"],
            unnecessary_complexity=["espuma"],
            missing_contrasts=[],
        ),
        "revision_count": 1,
        "max_revisions": 3,
    }
    assert after_fernando_review(state) == "revise"


def test_fernando_exhausted_finalizes_with_warning():
    state = {
        "fernando_review": FernandoReview(
            approved=False,
            score=7.0,
            feels_like_fernando=False,
            strengths=[],
            problems=["complexidade"],
            required_changes=["simplificar"],
            unnecessary_complexity=[],
            missing_contrasts=[],
        ),
        "revision_count": 3,
        "max_revisions": 3,
    }
    assert after_fernando_review(state) == "finalize_with_warning"
