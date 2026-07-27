# Handoff — product images

Written 2026-07-27. Branch `chore/graphify-fixture-rename`, pushed. HEAD `a5229f2c`.
661 tests pass.

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
| With a photo | 201 |
| Listed on the shop | 250 |
| Candidates pending staff review | 101 |
| Candidates approved | 25 |

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

`FIRECRAWL_API_KEY` in `.env` (gitignored); placeholder in `.env.example`.

## 4. Changes made

- Image pipeline end to end: `media_assets` (BYTEA + sha256 dedup), `products.image_id`,
  Pillow normalisation (800px WebP, EXIF stripped), `GET /api/v1/media/{id}`,
  storefront rendering with DrugIcon fallback
- `products.pack_size` + staff backfill flow
- Vitabiotics import: 178 products with photos, all unlisted/unpriced
- 496 brand names and 440 product names repaired (QA annotations, truncation)
- Unpriced products now show "Price on request" with no Add button (they showed ₦0)
- Matching: NAFDAC → brand+strength+form → brand+form (opt-in, flagged, extra gate)

## 5. Failed attempts

Do not retry:
- **Pinterest / image search / DailyMed** — copyright, and DailyMed is a US registry
  (Afrab 0, Emzor 0, Chemiron 0 hits)
- **NAFDAC Greenbook for photos** — detail pages carry only the NAFDAC logo (verified)
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
  ~100 of a first 216-row dry run were debris.

## 6. Next steps

1. **Review the 101 pending candidates** — Telegram → Products → 🖼 Review Image
   Candidates. Nothing else adds value until this moves. 85 are NAFDAC-matched
   (pack-size confirmation only); the rest also ask about strength.
2. **559 draft products ready to create** from 17 crawls. Dry-run only, NOT written.
   `python -m scripts.import_unmatched_products <crawl.json> --manufacturer "<name>" --commit`
   Check a sample of names first — the last two dry runs both surfaced quality problems,
   and some titles still come from alt text (e.g. lowercase "coatal soft gelatin tablet").
3. **Greenbook data import** — `import_greenbook.py` built, run only as far as applicant
   discovery. 9,021 registry records join on `nafdac_number`; **1,273 of our products
   lack a form or strength and have an NRN**. Fills empty fields only, reports conflicts.
   Also raises future match rates.
4. **Demo video still paused** — `docs/video/RECORDING-GUIDE.md`; resumes once hero
   products have photos.
5. Untouched issues: `peacewayonline.com.ng` DNS-fails but is hardcoded in
   `app/core/config.py` and `web/public/sitemap.xml`; `app/api/v1/prescriptions.py`
   discards web-uploaded prescription images.
