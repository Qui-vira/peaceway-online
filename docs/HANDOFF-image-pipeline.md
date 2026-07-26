# Handoff — manufacturer product-image pipeline

**Written 2026-07-26.** Branch `chore/graphify-fixture-rename`, pushed to origin.
Nothing in Tracks 1–3 is deployed. Last deploy was the Track-0 media pipeline.

---

## Where we are

| Track | Status |
|---|---|
| 0 — verification of manufacturer sites | ✅ done (see `docs/video/RECORDING-GUIDE.md` context) |
| 1 — data backfill (`pack_size` + staff flow) | ✅ **built, not deployed, not committed** |
| 2 — image matcher + scrapers | ✅ **built, not deployed, not committed** |
| 3 — Vitabiotics import | 🔶 **IN PROGRESS — feed verified, no code written yet** |
| 4 — staff approval flow | ⬜ not started |

**497 tests passing.** Full suite green at time of writing.

---

## Track 3 — exactly where I stopped

The feed is confirmed working. **This is the one thing that was hard to find, do not
re-derive it:**

`urllib` gets **HTTP 429**. The feed only responds to browser impersonation:

```python
from curl_cffi import requests
r = requests.get(url, impersonate="chrome", timeout=45)   # -> 200
```

`curl_cffi` is already installed (it ships with Scrapling).

**Feed shape**, verified from page 1:

```
URL   https://www.vitabiotics.com/collections/all-vitabiotics-products/products.json?limit=250&page=N
page 1 returned 178 products  (so likely 1-2 pages total)

product keys: id, title, handle, vendor, product_type, tags,
              variants[], images[], body_html, created_at, updated_at, published_at

sample:
  title        "Ultra Mushroom Gummies"
  handle       "ultra-mushroom-gummies"
  vendor       "Ultra"                <-- sub-brand, NOT "Vitabiotics"
  product_type "Gummies"              <-- maps cleanly to dosage_form
  variants[0]  option1="60 Gummies", price="19.95" (GBP - DO NOT IMPORT), sku, available
  images[0]    https://cdn.shopify.com/.../BLWKD050J14WL1E_Front_Small_<uuid>.png?v=1773138738
```

**Open question I had not resolved when I stopped:** `vendor` is the sub-brand
("Ultra", presumably also "Feroglobin", "Pregnacare", "Wellman"), while
`manufacturer` is specified as `"Vitabiotics"`. Using `vendor` for `brand_name` looks
right and avoids parsing the title, but confirm before relying on it.

### Track 3 rules (from the brief, non-negotiable)

- `is_listed = FALSE` on every imported product, no exception.
- **Import no prices.** Feed is GBP. Leave price null; staff set Naira.
- `nafdac_number = NULL`, `requires_review = TRUE` on every row.
- `manufacturer = "Vitabiotics"`.
- `brand_name`, `dosage_form`, `pack_size` from feed text only. **If any cannot be
  read directly, leave null and flag it. Do not guess.**
- Images go through `app/services/file_storage.py` into `media_assets`, linked by
  `products.image_id`, with `source_url` and `match_basis="vitabiotics-shopify-feed"`.
  This is the manufacturer's own photo of its own product, so there is no
  cross-matching risk — unlike Track 2, setting `image_id` here is correct.
- Strip `?v=` cache token and any `_NNNxNNN` size suffix for full resolution.
- Rate limit 3 seconds between page fetches.
- Report imported count and every product with a null field.

### Blocking prerequisite for Track 3

`media_assets` has **no `source_url` or `match_basis` columns yet**. The brief's
safety constraint #5 ("persist source_url and match_basis on every media asset")
requires adding them:

1. migration off head `c9d4e7f21a58`
2. add columns to `app/models/media.py`
3. extend `file_storage.store_image()` to accept and persist them

Do this before writing the importer.

---

## What Tracks 1 and 2 delivered

**Track 1 — backfill**
- `products.pack_size` column, migration `b8f3a2d61c47`
- `apply_change()` extended with brand_name / manufacturer / dosage_form / strength /
  pack_size, so edits land in `price_history` + `admin_activity_logs`
- Staff flow `app/bot/staff/products_backfill.py`, menu button "🧩 Backfill Product Data"
- Queue serves listed products first; `-` clears a field; nothing auto-populated
- Real counts: **42 of 51 listed** products need data; 1,561 of 8,624 catalogue-wide

**Track 2 — matcher**
- `image_candidates` staging table, migration `c9d4e7f21a58`
- `app/services/image_matching.py` — exact match on brand AND strength AND form
- `scripts/scrapers/` — six modules (emzor, afrab_chem, greenlife, embassy_pharma,
  may_baker, ac_drugs) + `base.py`
- `scripts/scrape_manufacturer_images.py` — dry-run by default, `--commit` to stage

**Scrapling gotchas already solved:**
- `robots_txt_obey` **does not exist** in 0.4.11 — robots is enforced manually in
  `scripts/scrapers/base.py` with Protego, failing closed on error
- `adaptive` is class-level: `StealthyFetcher.configure(adaptive=True)`
- Must use `async_fetch`, not `fetch` — sync Playwright cannot run inside asyncio

**Normalization decision — RATIFIED BY OWNER, keep it:** comparison is
whitespace-canonical (casefold, collapse whitespace, drop the space between a number
and its unit), so `500mg` == `500 mg`. Still exact: `500mg` != `50mg`. Every
transformation is logged into `match_basis`.

---

## The finding that caps everything

`brand_name` in the catalogue is not a brand. The PharmaOS import left product names,
dosage forms and QA annotations inside it:

```
EM-B-PLEX Syrup## (Strength format
Emcap Extra Tablet## (check pack size
Emcap Suspension** (duplicate, different product
```

Across 8,005 products with a brand: **337** carry `##`/`**` annotations, **663** an
unclosed `(`, **188** look truncated, **875** have the dosage form inside the brand.
Only **6,326** are clean enough to match on.

Live Emzor dry run: 111 images scraped, **1 matched**, 110 correctly refused. The
matcher is working; the catalogue is the bottleneck. **Owner has not yet decided
whether brand_name cleanup becomes its own track.**

---

## How to resume

```bash
cd C:\Projects\peaceway-online
./.venv/Scripts/python.exe -m pytest -q          # expect 497 passed
```

Dry-run a scraper (writes nothing):

```bash
./.venv/Scripts/python.exe -m scripts.scrape_manufacturer_images --manufacturer emzor
```

**Uncommitted work in the tree** — Tracks 1 and 2 are not committed. `AGENTS.md`,
`.impeccable/critique/` and `presentations/` were already modified before this work
and are not mine.

**Deploy procedure** is in memory at `peaceway-deploy-gotchas.md`: Vercel from the
repo ROOT (never `web/`), anchored `.vercelignore`, `railway up --service web --ci`,
and always check the build's route table with `vercel inspect <url> --logs` before
promoting.
