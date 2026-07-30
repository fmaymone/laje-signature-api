from app.composition.blocks_composer import (
    complete_from_catalogs,
    compose_from_library_v01,
    detect_protagonist_id,
    select_flavor_blocks,
)
from app.composition.library_v01 import load_library


def test_library_v01_counts():
    lib = load_library()
    assert len(lib["ingredients"]) == 100
    assert len(lib["flavor_blocks"]) == 100
    assert len(lib["compatibility_rules"]) == 25
    assert len(lib["conflict_rules"]) == 20
    assert len(lib["acidity_sources"]) == 20
    assert len(lib["textures"]) == 20
    assert len(lib["aromatic_families"]) == 15
    assert len(lib["bases"]) == 20


def test_detect_sirigado_id():
    assert detect_protagonist_id(["1,5 kg de sirigado", "milho"]) == "sirigado"


def test_detect_lagosta_alias():
    assert detect_protagonist_id(["Quero um prato com lagosta"]) == "lagosta_vermelha"
    assert detect_protagonist_id(["lagosta"]) == "lagosta_vermelha"


def test_select_blocks_for_sirigado():
    selection = select_flavor_blocks(
        protagonist_id="sirigado",
        mentions=["sirigado", "milho", "manteiga de garrafa", "churrasqueira"],
        max_blocks=4,
    )
    ids = [block["id"] for block in selection["selected_blocks"]]
    assert ids


def test_catalogs_fill_missing_roles():
    selection = select_flavor_blocks(
        protagonist_id="sirigado",
        mentions=["sirigado"],
        max_blocks=1,
    )
    completed = complete_from_catalogs(
        selection,
        equipment=["Thermomix TM7", "churrasqueira"],
        current_month=1,
    )
    assert completed.get("catalog_picks") is not None
    assert "seasonality_notes" in completed
    assert any("sirigado" in note for note in completed["seasonality_notes"])
    # single thin block should pull at least one catalog family
    assert len(completed["catalog_picks"]) >= 1


def test_defeso_alert_in_august():
    selection = select_flavor_blocks(
        protagonist_id="sirigado",
        mentions=["sirigado", "milho"],
        max_blocks=2,
    )
    completed = complete_from_catalogs(selection, current_month=8)
    assert any("ALERTA defeso" in note for note in completed["seasonality_notes"])


def test_pipeline_uses_catalogs():
    resolved, architecture = compose_from_library_v01(
        mentions=[
            "sirigado",
            "milho verde",
            "manteiga de garrafa",
            "limão",
            "churrasqueira",
            "TM7",
        ],
        max_blocks=4,
        equipment=["Thermomix TM7", "churrasqueira"],
    )
    assert resolved["selected_blocks"]
    assert architecture.protagonist == "sirigado"
    assert "catalog_picks" in resolved
    assert "seasonality_notes" in resolved
