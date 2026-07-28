from app.composition import (
    apply_regional_filter,
    compose_architecture,
    detect_protagonist,
    load_blocks,
    load_families,
    load_ingredients,
)


def test_library_loads():
    assert len(load_ingredients()) >= 30
    assert len(load_blocks()) >= 15
    assert len(load_families()) >= 5


def test_detect_sirigado():
    assert detect_protagonist(["1,5 kg de sirigado", "milho"]) == "sirigado"


def test_regional_substitution():
    report = apply_regional_filter(["batata", "manteiga de garrafa", "sirigado"])
    assert "macaxeira" in report.allowed_ingredients
    assert any("batata" in item for item in report.substitutions_applied)
    assert "sirigado" in report.allowed_ingredients


def test_compose_sirigado_milho():
    architecture = compose_architecture(
        protagonist="sirigado",
        mentions=["sirigado", "milho", "manteiga de garrafa", "churrasqueira"],
        max_blocks=5,
    )
    assert architecture.protagonist == "sirigado"
    assert architecture.family_id == "mar_coco_citrico"
    roles = {block.role for block in architecture.blocks}
    assert "protagonist" in roles
    assert len(architecture.blocks) <= 5
    assert architecture.sensory_estimate.fat >= 0
