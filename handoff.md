# Handoff — product images

Written 2026-07-27. Branch `chore/graphify-fixture-rename`. HEAD `1cdb2dcf`, plus
uncommitted changes to `app/services/greenbook.py`, `scripts/import_greenbook.py`
and `tests/test_greenbook.py` (see §4). 666 tests pass.

(Replaces the previous handoff covering the staff checklist / meeting tracker — that
work shipped and had no blocking steps; see git history for `handoff.md` before this.)

## 1. Goal

Put real product photographs on the storefront for a 8,802-product catalogue, without
ever showing a photo of the wrong pack, strength or manufacturer.

## 2. Current state

Production deployed and healthy (Railway `web` + `worker`, Vercel).

| | |
|---|---:|
| Products | 8,802 |
| With a photo | 283 |
| Listed on the shop | 250 |
| Listed **and** photographed | 201 |
| Candidates pending staff review | 16 |
| Candidates approved | 109 |
| Candidates rejected | 1 |

The 82 photographed-but-unlisted products are mostly the Vitabiotics import, which
came in unlisted and unpriced deliberately.

**Scraping cannot reach 8,500 — verified, not assumed.** Of 50 manufacturers checked,
15 have no website and only 3 (Me Cure, Afrab-Chem, Jawa) publish NAFDAC registration
numbers, the only identifier that reliably matches. Those 3 produced 109 of the 128
candidates ever found. Realistic ceiling 200–400; the rest need staff photography via
the live `📷 Add Photo` flow.

## 3. Active files

Deployed (`app/services/`): `image_matching.py` (3-tier matcher),
`catalogue_markdown.py` (generic parser for any crawled site), `greenbook.py`,
`product_creation.py`, `image_candidates.py`, `file_storage.py`.
Staff UI: `app/bot/staff/image_candidates.py`, `products.py`, `products_backfill.py`.

Dev-only (`scripts/`, excluded from the container by `.railwayignore`):
`crawl_manufacturer.py` → `ingest_crawled_catalogue.py` → `sweep_manufacturers.py`,
plus `probe_nafdac_publishers.py`, `import_unmatched_products.py`,
`import_greenbook.py`, `import_vitabiotics.py`, `clean_brand_names.py`,
`approve_candidates.py`. Crawl→manufacturer map: `scripts/video/out/crawls/_map.json`.
Greenbook page cache: `scripts/video/out/greenbook/` (344 applicant pages + the
applicant index). Re-running the import costs no Firecrawl credits while it exists.

`FIRECRAWL_API_KEY` in `.env` (gitignored); placeholder in `.env.example`.

### Reaching the production database from a laptop

Railway's `DATABASE_URL` is an internal hostname that only resolves inside their
network, so `railway run python -m scripts.…` fails with `getaddrinfo failed`. Run
under `railway run --service Postgres`, which injects `DATABASE_PUBLIC_URL`, and
rewrite it to the asyncpg dialect before importing `app.core.db`.

## 4. Changes made

- Image pipeline end to end: `media_assets` (BYTEA + sha256 dedup), `products.image_id`,
  Pillow normalisation (800px WebP, EXIF stripped), `GET /api/v1/media/{id}`,
  storefront rendering with DrugIcon fallback
- `products.pack_size` + staff backfill flow
- Vitabiotics import: 178 products with photos, all unlisted/unpriced
- 496 brand names and 440 product names repaired (QA annotations, truncation)
- Unpriced products now show "Price on request" with no Add button (they showed ₦0)
- Matching: NAFDAC → brand+strength+form → brand+form (opt-in, flagged, extra gate)
- **72 NAFDAC-matched candidates bulk-approved** via
  `python -m scripts.approve_candidates --nafdac-only --commit`, which routes through
  the same service function as the Telegram flow (photos 201 → 283)
- **Greenbook import run to completion** — see §5 for what it actually yielded

Uncommitted (`app/services/greenbook.py`, `scripts/import_greenbook.py`,
`tests/test_greenbook.py`): the three bug fixes in §5, plus `--only-gaps`.

## 5. The Greenbook import — done, and what it really gave us

Run 2026-07-27 against production. **It filled 4 fields, not 1,273.** The earlier
estimate counted empty columns; it never asked whether the registry had anything to
put in them.

| | |
|---|---:|
| Applicant pages crawled (`--only-gaps`) | 344 |
| Registry records collected | 4,059 |
| Our products with an NRN and an empty field | 1,273 |
| …whose NRN the crawl found | 1,265 |
| …**blank in the registry too** | 1,256 |
| Actually filled | **4** |
| Conflicts reported and left alone | 345 |

The reason is category, not crawl coverage:

| category of the 1,261 un-fillable rows | |
|---|---:|
| Medical Devices | 1,070 |
| Veterinary | 76 |
| Supplements | 71 |
| Medicines | 30 |
| Vaccines | 13 |

Glucose monitors, lancets, baby diapers, sanitary pads and wipes have no dosage form
or strength, and NAFDAC records none either. **Do not re-run this expecting a bulk
fill.** 1,269 rows still have an empty form or strength and that is mostly correct.

The 4 writes (all `strength`, all reversible via `price_history`):
`B4-1398` De-Shalom Multivitamin Syrup, `04-3926` Lady's Own Tonic,
`04-9610` Zevit Liqui-Tab Float Caps, `A11-100708` Reventin Blood Tonic.

The 345 conflicts are all one benign pattern — **ours is more specific than the
registry's**: `Powder for injection` vs `injection`, `Vaginal capsule` vs `capsule`,
`Granules for suspension` vs `Granules`. Correctly left alone. Nothing to fix.

### One NAFDAC number is not always one product

Measured across the 4,058 distinct NRNs crawled: **313 are listed more than once, and
107 of those disagree on form or strength** (58 on form, 79 on strength).

    03-3183  Avro Antibacterial Handwash 0.5%  vs  Avro Hand Sanitizer 70%
    04-0396  Emcillin Suspension               vs  Emcillin Powder for Oral Suspension
    04-0268  Folic Acid Tablet 5 mg            vs  Bcosam Tablet (no strength)

This matters wherever an NRN alone is treated as proof of identity. Only 4 of the 126
image candidates sit on such an NRN, and all 4 are now approved. One deserves a look:
**`A11-0662` Zing C Tablet**, whose number covers both *Tablet* and *Chewable tablet*
while our record says Tablet. If the live photo shows the chewable pack, clearing
`products.image_id` on that row reverts it.

### Three bugs found and fixed while running it

- **Wrong-strength writes.** 5 of the first 9 candidate fills were wrong. *Bcosam
  Tablet* would have taken `5 mg` from a registry row named *Folic Acid Tablet*, and
  *Emzoron Capsules* a `160 mg/15 mL` liquid strength from *Emzoron Tonic*. A value is
  no longer carried between entries whose names differ; only same-named entries
  (re-registrations of one product) may complete each other.
- **`'Pending'` parsed as a strength.** Now a placeholder alongside `NA` and
  `see Composition`.
- **`Event loop is closed` after the hour-long crawl.** The script enters asyncio
  twice around the module-level `app.core.db.engine`, so the second run inherited
  pooled connections from a dead loop. `run_async()` disposes the pool each time.
  Latent since the script was written — only the `--applicants` path had ever run.

## 6. Failed attempts

Do not retry:
- **Pinterest / image search / DailyMed** — copyright, and DailyMed is a US registry
  (Afrab 0, Emzor 0, Chemiron 0 hits)
- **NAFDAC Greenbook for photos** — detail pages carry only the NAFDAC logo (verified)
- **Greenbook for bulk form/strength backfill** — §5. The gap is real but the registry
  cannot close it.
- **Re-importing from PharmaOS to fix brands** — the pollution is in PharmaOS and in
  the Greenbook above it; `import_pharmaos.py` now strips on import
- **Crawling down the product-count ranking** — wrong sort; Me Cure ranks 13th and beat
  the other nineteen combined. Probe for NAFDAC publishers instead.
- **Firecrawl `onlyMainContent: true`** — strips the description holding the NRN, form
  and pack size. Must stay `False`.
- **Scrapling `css_first`** — does not exist; also no `robots_txt_obey` (enforced
  manually with Protego, fails closed), `adaptive` is class-level, `async_fetch`
  required under asyncio

Bugs fixed, worth knowing:
- Block-bleed paired a caplet photo with a suspension. Block text is trusted only when
  the image has its own heading; NRNs only within 400 chars.
- `pack=<none>` in `match_basis` made Telegram reject the whole review message, so the
  buttons looked dead. Now `pack=(none)` + every interpolation HTML-escaped.
- `_title_for` fell back to stripped markdown, producing names like `)](https://…` —
  ~100 of a first 216-row dry run were debris. Related: many approved candidates still
  carry marketing copy as `scraped_title` ("An Ideal Stool Softener"). The title is
  cosmetic — matching used the NRN — but it makes eyeballing a batch useless.

## 7. Next steps

1. **16 candidates still pending**, all matched on brand+form only with
   `STRENGTH NOT MATCHED` in the basis (Bioszime Injection, Chexol Tablets, Iron Dex,
   Larykul, Ketineal Cream…). These are exactly the ones a human should judge:
   Telegram → Products → 🖼 Review Image Candidates.
   Lotexin was the first rejection: we do not stock it, and the product row stays
   unlisted rather than deleted so the rejection survives the next Geneith crawl.
2. **559 draft products ready to create** from 17 crawls. Dry-run only, NOT written.
   `python -m scripts.import_unmatched_products <crawl.json> --manufacturer "<name>" --commit`
   Check a sample of names first — the last two dry runs both surfaced quality problems,
   and some titles still come from alt text (e.g. lowercase "coatal soft gelatin tablet").
3. **82 products have a photo but are not listed** (mostly Vitabiotics, unpriced).
   Pricing them is what turns those photos into storefront value.
4. **Demo video still paused** — `docs/video/RECORDING-GUIDE.md`; resumes once hero
   products have photos.
5. Untouched issues: `peacewayonline.com.ng` DNS-fails but is hardcoded in
   `app/core/config.py` and `web/public/sitemap.xml`; `app/api/v1/prescriptions.py`
   discards web-uploaded prescription images.
