"""NAFDAC Greenbook applicant-page parsing.

Fixture is the real markdown from
https://greenbook.nafdac.gov.ng/applicant/products/82 (Afrab-Chem), fetched
2026-07-27. Every NRN in it exists in the production catalogue.
"""
from __future__ import annotations

from app.services.greenbook import parse_applicant_page

REAL = r"""## Products of Afrab-Chem Limited.

[**Chloraf Suspension\#\# Suspension** Chloramphenicol Palmitate \\
\\
125 mg/5 mL\\
\\
NRN: 04-0543](https://greenbook.nafdac.gov.ng/products/details/266)

[**Afrab Loratadine Syrup\*\* Syrup** Loratadine \\
\\
5 mg/5 mL\\
\\
NRN: A4-7551](https://greenbook.nafdac.gov.ng/products/details/6486)

[**Banedif Ointment\#\# (strength format) Ointment** Zinc Bacitracin; Neomycin Sulphate; Zinc oxide \\
\\
126.90mg; 181.69mg;11.71mg\\
\\
NRN: 04-2046](https://greenbook.nafdac.gov.ng/products/details/6534)

[**Nospamin Drops Solution/Drops** Homatropine Methylbromide \\
\\
2 mg/mL\\
\\
NRN: 04-0210](https://greenbook.nafdac.gov.ng/products/details/775)

[**Afrabvite Multivitamin Drops\*\* Liquid** Vitamins \\
\\
see Composition\\
\\
NRN: 04-0213](https://greenbook.nafdac.gov.ng/products/details/7436)

[**Afrab Zinc Tablets 20 mg\#\# Dispersible tablet** Zinc (Zinc Sulfate) \\
\\
20 mg\\
\\
NRN: A11-100004](https://greenbook.nafdac.gov.ng/products/details/2974)
"""


def _by_nrn():
    return {r.nafdac: r for r in parse_applicant_page(REAL)}


def test_finds_every_record():
    assert len(parse_applicant_page(REAL)) == 6


def test_extracts_registration_number():
    assert "A4-7551" in _by_nrn()


def test_extracts_dosage_form_from_the_label():
    recs = _by_nrn()
    assert recs["A4-7551"].form.lower() == "syrup"
    assert recs["04-2046"].form.lower() == "ointment"


def test_handles_multi_word_forms():
    recs = _by_nrn()
    assert recs["04-0210"].form.lower() == "solution/drops"
    assert recs["A11-100004"].form.lower() == "dispersible tablet"


def test_extracts_strength():
    recs = _by_nrn()
    assert recs["A4-7551"].strength == "5 mg/5 mL"
    assert recs["04-0543"].strength == "125 mg/5 mL"


def test_multi_ingredient_strength_kept_verbatim():
    assert _by_nrn()["04-2046"].strength == "126.90mg; 181.69mg;11.71mg"


def test_placeholder_strength_becomes_none():
    """'see Composition' is a pointer, not a strength."""
    assert _by_nrn()["04-0213"].strength is None


def test_extracts_active_ingredients():
    assert _by_nrn()["A4-7551"].ingredients == "Loratadine"


def test_strips_nafdacs_own_review_annotations_from_the_name():
    """These come from the registry itself, not from our import."""
    recs = _by_nrn()
    assert recs["04-2046"].name == "Banedif Ointment"
    assert recs["A4-7551"].name == "Afrab Loratadine Syrup"
    assert "##" not in recs["04-0543"].name


def test_name_excludes_the_trailing_form():
    assert _by_nrn()["04-0543"].name == "Chloraf Suspension"


def test_keeps_the_detail_url():
    assert _by_nrn()["A4-7551"].detail_url.endswith("/products/details/6486")


def test_empty_input_is_safe():
    assert parse_applicant_page("") == []
    assert parse_applicant_page("no entries here") == []


def test_duplicate_nrn_deduped():
    assert len(parse_applicant_page(REAL + REAL)) == 6


def test_agreeing_duplicates_keep_their_values():
    recs = {r.nafdac: r for r in parse_applicant_page(REAL + REAL)}
    assert recs["A4-7551"].form.lower() == "syrup"
    assert recs["A4-7551"].strength == "5 mg/5 mL"


# The registry lists one NRN twice for genuinely different packs. Real example from
# https://greenbook.nafdac.gov.ng/applicant/products/167 (Emzor), fetched 2026-07-27:
# A4-7579 is both a 125 mg/5 mL suspension and 100 mg/15 mL drops.
CONFLICTING = r"""[**Emcap Suspension\*\* (duplicate) Suspension** Paracetamol \\
\\
125 mg/5 mL\\
\\
NRN: A4-7579](https://greenbook.nafdac.gov.ng/products/details/1)

[**Emzor Paracetamol Drops\#\# (see A4-7579) Drops** Paracetamol \\
\\
100mg/15ml\\
\\
NRN: A4-7579](https://greenbook.nafdac.gov.ng/products/details/2)
"""


# 04-0268 covers two unrelated products; only one carries a strength.
DIFFERENT_PRODUCTS = r"""[**Folic Acid Tablet Tablet** Folic Acid \\
\\
5 mg\\
\\
NRN: 04-0268](https://greenbook.nafdac.gov.ng/products/details/1)

[**Bcosam Tablet\#\# (duplicate) Tablet** Vitamin B Complex \\
\\
NRN: 04-0268](https://greenbook.nafdac.gov.ng/products/details/2)
"""


def test_a_value_is_not_borrowed_across_two_different_products():
    """One NRN, two products: Bcosam must not inherit folic acid's 5 mg."""
    recs = parse_applicant_page(DIFFERENT_PRODUCTS)
    assert len(recs) == 1
    assert recs[0].strength is None


def test_same_product_listed_twice_may_complete_itself():
    """A re-registration of one product can fill in what the other entry omits."""
    twice = r"""[**Omega-3 Fish Oil Capsules Capsule** Fish Oil \\
\\
NRN: A4-8330](https://greenbook.nafdac.gov.ng/products/details/1)

[**Omega-3 Fish Oil Capsules\*\* Capsule** Fish Oil \\
\\
1000 mg\\
\\
NRN: A4-8330](https://greenbook.nafdac.gov.ng/products/details/2)
"""
    assert parse_applicant_page(twice)[0].strength == "1000 mg"


def test_pending_strength_is_a_placeholder_not_a_value():
    entry = r"""[**Krishat Multivitamin Capsules Capsule** Multivitamins \\
\\
Pending\\
\\
NRN: A11-100180](https://greenbook.nafdac.gov.ng/products/details/1)
"""
    assert parse_applicant_page(entry)[0].strength is None


def test_conflicting_duplicates_report_the_field_as_unknown():
    """Never pick one of two disagreeing strengths for a medicine — say we don't know."""
    recs = parse_applicant_page(CONFLICTING)
    assert len(recs) == 1
    assert recs[0].form is None
    assert recs[0].strength is None
