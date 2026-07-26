"""Brand-name cleanup: strip QA annotations, leave real product information alone.

The dangerous failure here is over-eager stripping. "Chemilife Daily Multivitamin
Drops (Orange flavour" and "Huggies Dry Comfort (Mini) Size 2" carry real product
information; removing it would quietly change what a medicine record says.
"""
from __future__ import annotations

import pytest

from app.services.brand_cleanup import (
    MAX_RESTORE_TAIL,
    QA_NOTE_OPENERS,
    detect_issues,
    is_auto_fixable,
    restore_truncated_brand,
    strip_qa_annotation,
)


# ── Restoring brands truncated mid-bracket, using products.name ───────────────
@pytest.mark.parametrize(
    "brand,name,expected",
    [
        ("Coflax Cough Syrup (Adult", "Coflax Cough Syrup (Adult)", "Coflax Cough Syrup (Adult)"),
        ("Fest Diclofenac (duplicate", "Fest Diclofenac (duplicate)", "Fest Diclofenac (duplicate)"),
        ("Elox Hygiene Blaster Solution (Surface",
         "Elox Hygiene Blaster Solution (Surface Disinfectant)",
         "Elox Hygiene Blaster Solution (Surface Disinfectant)"),
        ("Alkum Cough Expectorant(non Drowsy", "Alkum Cough Expectorant(non Drowsy)",
         "Alkum Cough Expectorant(non Drowsy)"),
    ],
)
def test_restores_truncated_bracket_from_name(brand, name, expected):
    restored, note = restore_truncated_brand(brand, name)
    assert restored == expected
    assert note is not None


def test_restore_stops_at_the_closing_bracket():
    """`name` may carry strength or form after the bracket. That is not the brand."""
    restored, _ = restore_truncated_brand(
        "Coflax Cough Syrup (Adult", "Coflax Cough Syrup (Adult) 100 mL Syrup"
    )
    assert restored == "Coflax Cough Syrup (Adult)"


def test_no_restore_when_brand_is_not_a_prefix_of_name():
    restored, note = restore_truncated_brand("Totally Different (x", "Coflax Cough Syrup (Adult)")
    assert restored == "Totally Different (x" and note is None


def test_no_restore_when_brand_brackets_already_balance():
    restored, note = restore_truncated_brand("Emcap", "Emcap Paracetamol Caplet 500 mg")
    assert restored == "Emcap" and note is None


def test_no_restore_when_name_brackets_also_unbalanced():
    restored, note = restore_truncated_brand("Foo (bar", "Foo (bar baz")
    assert restored == "Foo (bar" and note is None


def test_no_restore_when_tail_is_implausibly_long():
    long_name = "Foo (bar" + " x" * MAX_RESTORE_TAIL + ")"
    restored, note = restore_truncated_brand("Foo (bar", long_name)
    assert restored == "Foo (bar" and note is None


def test_restore_handles_none():
    assert restore_truncated_brand(None, "x") == (None, None)
    assert restore_truncated_brand("x", None) == ("x", None)


def test_restore_only_ever_extends_the_existing_value():
    """Recovery appends the missing tail; it never rewrites what was already there."""
    brand = "Coflax Cough Syrup (Adult"
    restored, _ = restore_truncated_brand(brand, "Coflax Cough Syrup (Adult)")
    assert restored.startswith(brand)
    assert len(restored) > len(brand)


# ── Real values observed in production that MUST be cleaned ───────────────────
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Kadcep## (check dosage form", "Kadcep"),
        ("Bcosam Tablet## (duplicate, different product", "Bcosam Tablet"),
        ("Kemi Cream## (strength format", "Kemi Cream"),
        ("Fungusol Lotion## (check NRN", "Fungusol Lotion"),
        ("Cosmin Gel## (null smpc", "Cosmin Gel"),
        ("Pionorm 30 Tablets## (incomplete smpc", "Pionorm 30 Tablets"),
        ("KISIRETIC TABLET## (duplicate", "KISIRETIC TABLET"),
        # marker variants seen in the data: **, +++, )##, %##
        ("Exforge HCT 10 mg Tablets** (duplicate", "Exforge HCT 10 mg Tablets"),
        ("Kattle Care Multivitamin Injection+++ (check strength format",
         "Kattle Care Multivitamin Injection"),
        # no punctuation marker at all - 12 such rows exist
        ("Someria Syrup (check composition", "Someria Syrup"),
        # "_" is a \w character, so the marker class must include it explicitly
        ("Avrosart Tablet_ (incomplete smpc", "Avrosart Tablet"),
        # a legitimate parenthetical BEFORE the QA note must not hide the note,
        # and must survive the strip
        ("Huggies Dry Comfort (Mini) Size 2## (check pack size",
         "Huggies Dry Comfort (Mini) Size 2"),
        ("Emvit-C Tablet (White)## (pack size)", "Emvit-C Tablet (White)"),
        # a marker with NO bracket at all
        ("Neutroderm Cream**", "Neutroderm Cream"),
        ("Kaosider Tablet## $", "Kaosider Tablet"),
        ("Reberk 75 Capsules##$", "Reberk 75 Capsules"),
        # a marker whose note wording is outside the closed vocabulary: the marker
        # itself is the signal, so the vocabulary is not consulted
        ("Glomaxtra-XL## (dosage form)", "Glomaxtra-XL"),
        ("Nalis Ferrous Sulphate## (no NRN)", "Nalis Ferrous Sulphate"),
        ("Jawavite Multivitamin Syrup## (updates needed)", "Jawavite Multivitamin Syrup"),
        ("Silkplast** (incorrect Mfr country?)", "Silkplast"),
        ("Dolac-30 Injection## (pack size)", "Dolac-30 Injection"),
    ],
)
def test_strips_qa_annotations(raw, expected):
    cleaned, note = strip_qa_annotation(raw)
    assert cleaned == expected
    assert note is not None


# ── Real values that MUST survive untouched ───────────────────────────────────
@pytest.mark.parametrize(
    "raw",
    [
        "Huggies Dry Comfort (Mini) Size 2",
        "Chemilife Daily Multivitamin Drops (Orange flavour",
        "Cartef Tablet (80 mg/480 mg",
        "Always 3-In-1 Maxi Thick (Extra-Long",
        "Ak-Freedom (Newborn",
        "Veri-Q Hb Mate Hemoglobin (For Professional Use",
        "Anosan Eco (Room Hygiene & Nebulization",
        "Dr. Brown's (Mini",
        "Sharma Nails (Non-Sterile",
        "Emcap",
        "Afrab",
    ],
)
def test_leaves_real_product_information_alone(raw):
    cleaned, note = strip_qa_annotation(raw)
    assert cleaned == raw
    assert note is None


def test_unrecognised_opener_is_left_alone():
    """An unknown word means 'leave it', so new variants are never stripped."""
    cleaned, note = strip_qa_annotation("Wellman (Banana flavour")
    assert cleaned == "Wellman (Banana flavour" and note is None


def test_never_strips_the_whole_value():
    cleaned, note = strip_qa_annotation("## (check everything")
    assert cleaned == "## (check everything"
    assert note is None


def test_handles_none_and_blank():
    assert strip_qa_annotation(None) == (None, None)
    assert strip_qa_annotation("") == ("", None)


def test_vocabulary_excludes_real_product_words():
    """These appear as parenthetical openers in real data and carry product info."""
    for word in ("medium", "extra", "non", "long", "mini", "midi", "small",
                 "large", "size", "adult", "sterile", "absorbable", "for"):
        assert word not in QA_NOTE_OPENERS


# ── Issue classification ──────────────────────────────────────────────────────
def test_detects_qa_annotation():
    assert "qa_annotation" in detect_issues("Kadcep## (check dosage form")


def test_detects_unclosed_paren():
    assert "unclosed_paren" in detect_issues("Chemilife Drops (Orange flavour")


def test_detects_embedded_dosage_form():
    assert "form_embedded" in detect_issues("Emcap Extra Tablet")


def test_balanced_parens_are_not_an_issue():
    assert "unclosed_paren" not in detect_issues("Huggies Dry Comfort (Mini) Size 2")


def test_clean_brand_has_no_issues():
    assert detect_issues("Emcap") == []


def test_issues_judged_after_notional_cleanup():
    """A QA note's own unclosed paren must not also be reported as a truncation."""
    assert detect_issues("Kadcep## (check dosage form") == ["qa_annotation"]


def test_auto_fixable_only_for_qa_annotations():
    assert is_auto_fixable("Kadcep## (check dosage form") is True
    assert is_auto_fixable("Emcap Extra Tablet") is False
    assert is_auto_fixable("Chemilife Drops (Orange flavour") is False


# ── Cleaning improves matchability without inventing anything ─────────────────
def test_cleaned_brand_becomes_matchable():
    from app.services.image_matching import canonical

    cleaned, _ = strip_qa_annotation("Emcap## (check pack size")
    assert canonical(cleaned) == canonical("Emcap")


def test_cleanup_never_adds_characters():
    """Repair only ever removes. It cannot introduce a brand that was not there."""
    for raw in ("Kadcep## (check dosage form", "Kemi Cream## (strength format"):
        cleaned, _ = strip_qa_annotation(raw)
        assert cleaned in raw
        assert len(cleaned) < len(raw)
