"""Generic parser for crawled manufacturer Markdown.

Fixture below is the real Apify output for
https://www.afrabchem.com/product-category/anti-allergic/ — all three NRNs in it
exist in the production catalogue, so this is a true end-to-end shape.
"""
from __future__ import annotations

from app.services.catalogue_markdown import parse_blocks, parse_catalogue_markdown

REAL = """# Anti-Allergic – Afrab Chem Ltd

[![](https://www.afrabchem.com/wp-content/uploads/2013/06/allergin-300x300.jpg)](https://www.afrabchem.com/product/allergin-syrup/)

#### [Allergin Syrup](https://www.afrabchem.com/product/allergin-syrup/)

_Syrup_ (NRN: 04-1955): Chlorpheniramine maleate BP 2 mg per 5 mL.

_Pack size_: 60 mL plastic bottle.

[![](https://www.afrabchem.com/wp-content/uploads/2019/03/Loratadine-syr-3D-01-300x300.jpg)](https://www.afrabchem.com/product/loratadine-syrup/)

#### [Loratadine Syrup](https://www.afrabchem.com/product/loratadine-syrup/)

_Syrup_ (NRN: A4-7551): Loratadine 5 mg

_Pack size_: 60 ml Plastic bottle.

[![](https://www.afrabchem.com/wp-content/uploads/2019/03/Loratadine-10mg-3D-01-300x300.jpg)](https://www.afrabchem.com/product/loratadine-tablet/)

#### [Loratadine Tablet](https://www.afrabchem.com/product/loratadine-tablet/)

_Tablet_ (NRN: A4-7347): Loratadine 10 mg.

_Pack size_: Blister packs of 2 x 10 and 10 x 10.
"""


def _parse(md=REAL):
    return parse_catalogue_markdown(
        md, manufacturer="Afrab-Chem Limited",
        source_url="https://www.afrabchem.com/product-category/anti-allergic/",
    )


def test_finds_every_product_image():
    assert len(_parse()) == 3


def test_associates_the_right_text_with_each_image():
    items = _parse()
    lora = next(i for i in items if "Loratadine-syr" in i.image_url)
    assert lora.title.startswith("Loratadine Syrup")
    assert lora.nafdac == "A4-7551"
    assert lora.form == "syrup"


def test_extracts_nafdac_from_every_block():
    assert sorted(i.nafdac for i in _parse()) == ["04-1955", "A4-7347", "A4-7551"]


def test_does_not_bleed_one_products_nafdac_into_another():
    """The whole point of block-splitting: three NRNs, three distinct products."""
    items = _parse()
    assert len({i.nafdac for i in items}) == 3


def test_extracts_strength_and_pack():
    tab = next(i for i in _parse() if i.nafdac == "A4-7347")
    assert tab.strength == "10 mg"
    assert tab.form == "tablet"
    assert tab.pack_size is not None


def test_skips_site_chrome():
    md = REAL + "\n![](https://www.afrabchem.com/wp-content/uploads/afrab-logo_main.png)\n"
    assert all("logo" not in i.image_url for i in _parse(md))


def test_relative_image_urls_are_skipped():
    md = "![](/assets/img/local.png)\n\n#### Something\n"
    assert _parse(md) == []


def test_duplicate_images_deduped():
    md = REAL + REAL
    assert len(_parse(md)) == 3


def test_empty_markdown_is_safe():
    assert _parse("") == []
    assert parse_blocks("") == []


def test_no_nafdac_still_yields_an_item():
    """Unmatched scraped items are kept on purpose — they are the coverage gap."""
    md = "![](https://x.test/a.jpg)\n\n#### Some Product\n\nNo registration number here.\n"
    items = _parse(md)
    assert len(items) == 1 and items[0].nafdac is None


def test_parser_never_sets_a_product_id():
    """This module reads only; pairing is the matcher's job."""
    for i in _parse():
        assert not hasattr(i, "product_id")


# ── Brand decomposition: manufacturers put the form in the product name ───────
def test_form_is_removed_from_the_brand():
    """Site says "Iron Dex Capsules"; our catalogue stores brand "Iron Dex" + form
    "Capsule". Removing a form we already extracted is decomposition, not a guess."""
    from app.services.catalogue_markdown import brand_from_title

    assert brand_from_title("Iron Dex Capsules", "capsule", None, None) == "Iron Dex"
    assert brand_from_title("Ketineal Cream", "cream", None, None) == "Ketineal"
    assert brand_from_title("Ceflonac Tablets", "tablet", None, None) == "Ceflonac"


def test_brand_untouched_when_no_form_was_extracted():
    from app.services.catalogue_markdown import brand_from_title

    assert brand_from_title("Ceflonac Forte", None, None, None) == "Ceflonac Forte"
    assert brand_from_title("Boneflex", None, None, None) == "Boneflex"


def test_strength_and_pack_removed_from_brand():
    from app.services.catalogue_markdown import brand_from_title

    assert brand_from_title("Emcap 500mg Caplet 10*10", "caplet", "500mg", "10*10") == "Emcap"


def test_brand_never_becomes_empty():
    from app.services.catalogue_markdown import brand_from_title

    assert brand_from_title("Cream", "cream", None, None) is None


def test_unrecognised_words_are_kept():
    from app.services.catalogue_markdown import brand_from_title

    assert brand_from_title("Fenal 50 Mystery", None, None, None) == "Fenal 50 Mystery"


# ── Markdown debris must never become a product name ─────────────────────────
def test_rejects_markdown_debris_as_a_name():
    """These are real fallback outputs that would have become medicine records."""
    from app.services.catalogue_markdown import looks_like_a_product_name

    for junk in (
        ") [",
        ")](https://www.geneithpharm.com/product/coatal",
        "](https://x.test/y)",
        "https://www.geneithpharm.com/product/x",
        "www.example.com",
        "()",
        "-",
        "12345",
        "",
        None,
    ):
        assert looks_like_a_product_name(junk) is False, junk


def test_accepts_real_product_names():
    from app.services.catalogue_markdown import looks_like_a_product_name

    for good in (
        "Camosunate Adult Tablets",
        "Coatal Soft Gelatin Cap 20/120mg by 24",
        "Emcap 500mg Caplet",
        "Iron Dex Syrup",
        "P-Alaxin",
    ):
        assert looks_like_a_product_name(good) is True, good


def test_image_with_no_heading_and_no_alt_is_skipped():
    """No way to say what it shows, so it can be neither matched nor created."""
    md = "![](https://x.test/mystery.png)\n\n)](https://x.test/product/foo)\n"
    assert _parse(md) == []


def test_image_with_junk_alt_is_skipped():
    md = "![](https://x.test/a.png)\n\n![](https://x.test/b.png)\n"
    assert _parse(md) == []
