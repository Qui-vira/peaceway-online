"""Track 3 — Vitabiotics Shopify feed import.

The feed is a UK retail catalogue in GBP with no NAFDAC registration, so the import
rules are safety rules, not preferences: nothing listed, no prices, everything
flagged for pharmacist review.
"""
from __future__ import annotations

import pytest

from scripts.import_vitabiotics import (
    MANUFACTURER,
    MATCH_BASIS,
    Candidate,
    full_resolution,
    to_candidate,
)


def _feed_product(**over) -> dict:
    p = {
        "title": "Feroglobin Capsules",
        "handle": "feroglobin-capsules",
        "vendor": "Feroglobin",
        "product_type": "Capsules",
        "variants": [{"option1": "30 Capsules", "price": "9.95", "sku": "FGC030"}],
        "images": [{"src": "https://cdn.shopify.com/s/files/1/x/FGC030_Front.png?v=1773138738"}],
    }
    p.update(over)
    return p


# ── Image URL cleanup ─────────────────────────────────────────────────────────
def test_strips_cache_token():
    assert full_resolution("https://cdn.shopify.com/a/b.png?v=1773138738") == \
        "https://cdn.shopify.com/a/b.png"


def test_strips_size_suffix():
    assert full_resolution("https://cdn.shopify.com/a/b_300x300.png") == \
        "https://cdn.shopify.com/a/b.png"


def test_strips_both():
    assert full_resolution("https://cdn.shopify.com/a/b_1024x1024.jpg?v=999") == \
        "https://cdn.shopify.com/a/b.jpg"


def test_does_not_mangle_names_containing_x():
    """'_Front' and real filename parts must survive; only NNNxNNN is a size suffix."""
    url = "https://cdn.shopify.com/s/files/1/x/BLWKD050J14WL1E_Front_Small.png?v=1"
    assert full_resolution(url) == \
        "https://cdn.shopify.com/s/files/1/x/BLWKD050J14WL1E_Front_Small.png"


# ── Field reading: direct, never inferred ─────────────────────────────────────
def test_brand_comes_from_vendor_field():
    c = to_candidate(_feed_product())
    assert c.brand == "Feroglobin"


def test_form_comes_from_product_type():
    assert to_candidate(_feed_product()).form == "Capsules"


def test_pack_size_comes_from_single_variant():
    assert to_candidate(_feed_product()).pack_size == "30 Capsules"


def test_bundles_is_not_treated_as_a_dosage_form():
    """A bundle is a box of other products; it says nothing about the form inside."""
    c = to_candidate(_feed_product(product_type="Bundles"))
    assert c.form is None
    assert "dosage_form" in c.nulls


def test_blank_product_type_yields_null_not_a_guess():
    c = to_candidate(_feed_product(product_type=""))
    assert c.form is None and "dosage_form" in c.nulls


def test_missing_vendor_yields_null_not_parsed_from_title():
    c = to_candidate(_feed_product(vendor=""))
    assert c.brand is None
    assert "brand_name" in c.nulls


def test_multiple_variants_leave_pack_size_null_and_flagged():
    """Three pack sizes have no single correct answer, so we record none."""
    c = to_candidate(_feed_product(variants=[
        {"option1": "30 Capsules"}, {"option1": "60 Capsules"}, {"option1": "90 Capsules"},
    ]))
    assert c.pack_size is None
    assert any("ambiguous" in n for n in c.nulls)


def test_missing_image_is_flagged():
    c = to_candidate(_feed_product(images=[]))
    assert c.image_url is None and "image" in c.nulls


def test_clean_product_has_no_flags():
    assert to_candidate(_feed_product()).nulls == []


def test_source_url_points_at_the_product_page():
    c = to_candidate(_feed_product())
    assert c.source_url == "https://www.vitabiotics.com/products/feroglobin-capsules"


# ── The import rules that are safety rules ────────────────────────────────────
def test_price_is_never_read_from_the_feed():
    """The feed carries GBP prices. Nothing in the candidate may hold one."""
    c = to_candidate(_feed_product())
    assert not hasattr(c, "price")
    assert "9.95" not in repr(c)


def test_importer_source_declares_the_safety_constants():
    import scripts.import_vitabiotics as mod

    src = open(mod.__file__, encoding="utf-8").read()
    assert "is_listed=False" in src
    assert "nafdac_number=None" in src
    assert "requires_review=True" in src
    assert MANUFACTURER == "Vitabiotics"
    assert MATCH_BASIS == "vitabiotics-shopify-feed"


def test_importer_never_sets_a_selling_price():
    """ProductPricing is created empty; no price field is ever assigned."""
    import ast

    import scripts.import_vitabiotics as mod

    tree = ast.parse(open(mod.__file__, encoding="utf-8").read())
    assigned = {
        t.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        for t in node.targets
        if isinstance(t, ast.Attribute)
    }
    assert "selling_price" not in assigned
    assert "cost_price" not in assigned

    kwargs = {
        kw.arg
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for kw in node.keywords
        if kw.arg
    }
    assert "selling_price" not in kwargs
    assert "cost_price" not in kwargs


@pytest.mark.parametrize("field_name", ["is_listed", "requires_review", "nafdac_number"])
def test_safety_fields_are_set_literally_not_computed(field_name):
    """These must be constants in the source, not expressions that could vary."""
    import ast

    import scripts.import_vitabiotics as mod

    tree = ast.parse(open(mod.__file__, encoding="utf-8").read())
    values = [
        kw.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for kw in node.keywords
        if kw.arg == field_name
    ]
    assert values, f"{field_name} is never set"
    assert all(isinstance(v, ast.Constant) for v in values), (
        f"{field_name} is computed rather than a literal constant"
    )
