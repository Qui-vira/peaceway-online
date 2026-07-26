"""Track 2 — exact matching of scraped manufacturer images to catalogue products.

These tests exist to make the safety rule enforceable rather than aspirational:
a photo of the wrong pack, strength or manufacturer on a NAFDAC-regulated pharmacy
is a patient-safety failure. Anything below an exact brand+strength+form match must
produce no candidate.
"""
from __future__ import annotations

import pytest

from app.models import Product
from app.services.image_matching import (
    ScrapedItem,
    canonical,
    extract_form,
    extract_pack,
    extract_strength,
    match_against_catalogue,
    match_product,
    normalize_pack,
)


def _product(**over) -> Product:
    defaults = dict(
        name="Emcap 500mg Caplet",
        generic_name="Ampicillin/Cloxacillin",
        brand_name="Emcap",
        manufacturer="Emzor Pharmaceutical Industries Limited",
        dosage_form="Caplet",
        strength="500 mg",
        pack_size=None,
        is_listed=False,
        requires_prescription=False,
        requires_review=False,
    )
    defaults.update(over)
    p = Product(**defaults)
    p.id = over.get("id", "prod-1")
    return p


def _item(**over) -> ScrapedItem:
    defaults = dict(
        manufacturer="Emzor Pharmaceutical Industries Limited",
        source_url="https://emzorpharma.com/emzor-products/",
        image_url="https://www.emzorpharma.com/wp-content/uploads/2019/11/02-EmCAP-View-01.png",
        title="Emcap 500mg Caplet 10*10 -image",
        brand="Emcap",
        strength="500mg",
        form="caplet",
        pack_size="10*10",
    )
    defaults.update(over)
    return ScrapedItem(**defaults)


# ── Canonicalisation is meaning-preserving, not fuzzy ─────────────────────────
def test_canonical_is_case_insensitive():
    assert canonical("500MG") == canonical("500mg")


def test_canonical_ignores_space_between_number_and_unit():
    assert canonical("500 mg") == canonical("500mg")


def test_canonical_collapses_whitespace():
    assert canonical("  Emcap   Extra ") == "emcap extra"


def test_canonical_blank_is_empty():
    assert canonical(None) == "" and canonical("   ") == ""


# ── The refusal cases: these must NEVER match ─────────────────────────────────
def test_different_brand_rejected():
    r = match_product(_item(brand="Emcaps"), _product(brand_name="Emcap"))
    assert r.matched is False
    assert "brand differs" in r.reason


def test_near_miss_strength_rejected():
    """500mg vs 50mg is one character apart and a tenfold dosing error."""
    r = match_product(_item(strength="50mg"), _product(strength="500 mg"))
    assert r.matched is False
    assert "strength differs" in r.reason


def test_different_form_rejected():
    r = match_product(_item(form="syrup"), _product(dosage_form="Caplet"))
    assert r.matched is False
    assert "form differs" in r.reason


def test_ratio_strength_not_equal_to_simple_strength():
    r = match_product(_item(strength="5mg/5mL"), _product(strength="5 mg"))
    assert r.matched is False


def test_product_missing_brand_cannot_match():
    """The 42 hand-created listed products land here until Track 1 backfill runs."""
    r = match_product(_item(), _product(brand_name=None))
    assert r.matched is False
    assert "needs backfill" in r.reason


def test_product_missing_strength_cannot_match():
    r = match_product(_item(), _product(strength=None))
    assert r.matched is False and "needs backfill" in r.reason


def test_blank_never_matches_blank():
    r = match_product(_item(brand=None), _product(brand_name=None))
    assert r.matched is False


def test_ambiguous_match_is_rejected_not_guessed():
    a = _product(id="prod-a")
    b = _product(id="prod-b")
    r = match_against_catalogue(_item(), [a, b])
    assert r.matched is False
    assert "ambiguous" in r.reason


def test_no_candidate_when_nothing_matches():
    r = match_against_catalogue(_item(brand="Totally Different"), [_product()])
    assert r.matched is False
    assert r.product_id is None


# ── The accept case ───────────────────────────────────────────────────────────
def test_exact_match_across_notation_difference():
    """Emzor writes '500mg', our catalogue writes '500 mg'. Same strength."""
    r = match_product(_item(), _product())
    assert r.matched is True
    assert r.product_id == "prod-1"


def test_match_basis_records_the_literal_comparison():
    r = match_product(_item(), _product())
    assert "brand=emcap" in r.match_basis
    assert "strength=500mg" in r.match_basis
    assert "form=caplet" in r.match_basis
    assert "pack=10*10->100 units" in r.match_basis


def test_match_basis_states_pack_was_not_matched_on():
    r = match_product(_item(), _product())
    assert "pack not used for matching" in r.match_basis


def test_match_basis_logs_normalisation():
    r = match_product(_item(pack_size="10 * 10"), _product())
    assert "normalized:" in r.match_basis


# ── Pack normalisation is display-only ────────────────────────────────────────
def test_pack_expands_multiplier_to_total():
    n = normalize_pack("10*10")
    assert n.display == "100 units"
    assert any("expanded" in note for note in n.notes)


def test_pack_strips_spaces_around_multiplier():
    assert normalize_pack("10 * 10").display == "100 units"


def test_pack_lowercases_units():
    n = normalize_pack("100ML")
    assert n.display == "100ml"
    assert "lowercased units" in n.notes


def test_ml_and_mL_are_identical_after_normalisation():
    assert normalize_pack("100 mL").display == normalize_pack("100 ml").display


def test_pack_none_is_handled():
    n = normalize_pack(None)
    assert n.display is None and n.as_basis() == "pack=<none>"


@pytest.mark.parametrize("pack", ["10*10", "10 x 10", "30's", "100 mL", None])
def test_pack_normalisation_never_changes_the_match_decision(pack):
    """The core safety property: pack notation cannot turn a non-match into a match,
    nor a match into a non-match."""
    matched_with = match_product(_item(pack_size=pack), _product()).matched
    assert matched_with is True

    rejected_with = match_product(
        _item(pack_size=pack, strength="50mg"), _product(strength="500 mg")
    ).matched
    assert rejected_with is False


# ── Field extraction refuses to guess ─────────────────────────────────────────
def test_extract_strength_from_manufacturer_text():
    assert extract_strength("Emcap 500mg Caplet 10*10") == "500mg"


def test_extract_strength_returns_none_when_absent():
    assert extract_strength("Lonart") is None


def test_extract_form_uses_closed_vocabulary():
    assert extract_form("Emprofen E 400mg Soft Gel") == "soft gel"
    assert extract_form("Emcap 500mg Caplet") == "caplet"


def test_extract_form_returns_none_for_unknown_word():
    assert extract_form("Emzor Mystery Preparation") is None


def test_extract_pack_reads_multiplier():
    assert extract_pack("Emcap 500mg Caplet 10*10") == "10*10"


def test_extract_pack_returns_none_when_absent():
    assert extract_pack("Emcap Caplet") is None
