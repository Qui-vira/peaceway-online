# Handoff — product images

Written 2026-07-27. Branch `chore/graphify-fixture-rename`, now **fast-forwarded into
`main`**; both point at `ba569dd4`. Pushed. 666 tests pass.

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
| With a photo | 305 |
| Listed on the shop | 250 |
| **Listed and photographed** | **214** |
| Listed, still no photo | 36 |
| Candidates approved / rejected / pending | 131 / 5 / 4 |

**Scraping cannot reach 8,500 — verified, not assumed.** Of 50 manufacturers checked,
15 have no website and only 3 (Me Cure, Afrab-Chem, Jawa) publish NAFDAC registration
numbers, the only identifier that reliably matches. Realistic ceiling 200–400; the
rest need staff photography via the live `📷 Add Photo` flow.

**The number that matters is 36, not 8,497.** 8,461 photoless products are unlisted —
no customer ever sees them. See §8.

## 3. How this is deployed (read before touching the deploy)

- **`web` auto-deploys from `main`** on push. It is the FastAPI app *and* the Telegram
  bot (the webhook is registered at startup).
- **`worker` does NOT auto-deploy.** Ship it with `railway up --service worker` from a
  checkout of the branch you want. This is why the image-candidate review flow was
  live in Telegram for days while `main` did not contain the code for it.
- **Vercel** builds the Next.js frontend from `web/`; project `web`
  (`prj_Yp0yprOrunjFwCeWK0tUFux1Ogzq`). Check `.vercel/project.json` before any
  `vercel` command.

### Reaching the production database from a laptop

Railway's `DATABASE_URL` is an internal hostname that only resolves inside their
network, so `railway run python -m scripts.…` fails with `getaddrinfo failed`. Run
under `railway run --service Postgres`, which injects `DATABASE_PUBLIC_URL`, and
rewrite it to the asyncpg dialect before importing `app.core.db`.

## 4. Active files

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

## 5. The Greenbook import — done, and what it really gave us

Run 2026-07-27 against production. **It filled 4 fields, not 1,273.** The earlier
estimate counted empty columns; it never asked whether the registry had anything to
put in them.

| | |
|---|---:|
| Applicant pages crawled (`--only-gaps`) | 344 |
| Registry records collected | 4,059 |
| Our products with an NRN and an empty field | 1,273 |
| …**blank in the registry too** | 1,256 |
| Actually filled | **4** |
| Conflicts reported and left alone | 345 |

1,070 of the un-fillable rows are **medical devices** — glucose monitors, lancets,
diapers, sanitary pads — which have no dosage form or strength, and NAFDAC records
none either. **Do not re-run this expecting a bulk fill.**

The 345 conflicts are all one benign pattern — ours is more specific than the
registry's (`Powder for injection` vs `injection`). Correctly left alone.

### One NAFDAC number is not always one product

Across the 4,058 numbers crawled, **313 appear more than once and 107 of those
disagree on form or strength** (58 form, 79 strength).

    03-3183  Avro Antibacterial Handwash 0.5%  vs  Avro Hand Sanitizer 70%
    04-0396  Emcillin Suspension               vs  Emcillin Powder for Oral Suspension
    04-0268  Folic Acid Tablet 5 mg            vs  Bcosam Tablet (no strength)

`greenbook.merge_records()` drops any field two entries disagree on. Five of the
first nine candidate fills were wrong before this existed.

**The Greenbook publishes no product photographs.** Re-verified: the
`admin.greenbook.nafdac.gov.ng/uploadImage/smpc_files/…` URLs that look like photos
are SmPC **documents**.

## 6. The listed-49 push — what scraping can and cannot reach

Started at 49 listed products with no photo, 41 of them with no manufacturer recorded.
Ended with **13 photographed and 25 manufacturers identified**.

**An empty `manufacturer` column means our record is incomplete, not that the maker is
unknowable.** Four came straight from the pharmacy; the rest from the maker's own site
or the registry.

Sources that worked, cheapest first:

1. **The cached Greenbook applicant pages** — free, on disk, authoritative. Exact
   product-name matches gave Durex→Reckitt, DE-DEON'S→Daily-Need, Orheptal→Farmex
   Meyer, Tuxil-D→Fidson, Liquid Iron→Adler, Nutracid→Sabiz, Dr. Fizzo→Juvee.
2. **Firecrawl image search** (`sources:["images"]`) — found Sygen (Colipan,
   Broncholyte) and the Dabur clove gel. Plain web search had missed all three.
3. **Filtering hits by the maker's own domain**, not a hand-written noise list. This
   is what caught that the top "Colipan" images were an unrelated Italian supplement.

Sources that returned nothing: all 17 existing crawls (860 parsed items, zero real
matches), Wayback for `ruzushop.com` (the availability API says archived; the snapshot
serves archive.org's own interstitial), and the sites of Fidson, Glenmark, Dana,
Juvee, Sabiz and Farmex Meyer — all JS shells or dead domains.

Photos published: Calamine Lotion (Ugo Lab), Canderm + Polygel (Shalina), Chemiron,
MenthoDex (Bell's), Astymin (Tablets India), Colipan + Broncholyte (Sygen), AC-Drex +
AC-Ibu (A.C. Drugs), DE-DEON'S (Daily-Need), and three Dabur toothpastes.

**Rejected rather than guessed:** Oak-Faith's calamine (the image sits on a generic
products page, not a calamine page), IBUCAP Sachet (Shalina publishes Caps, Forte,
Gel, Night — no sachet), and Durex (the UK shop sells Intensity/Nude in 10–25 packs;
ours is a Fetherlite 3-pack).

### 4 candidates are stuck on the manufacturers' own TLS

| host | problem | products |
|---|---|---|
| `chezresourcespharma.com` | certificate **expired** | Bioszime ×2, Chexol |
| `tabletsindia.com` | omits its intermediate certificate | Astymin |

Both serve the image with verification disabled. **Do not add `verify=False`** to the
download path — it publishes medicine photos, and that trades a visible failure for a
silent one. These need the manufacturer to fix their cert, or a staff photo.

## 7. Failed attempts

Do not retry:
- **Pinterest / image search / DailyMed** — copyright, and DailyMed is a US registry
- **NAFDAC Greenbook for photos** — §5, re-verified
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
- **Photographing the commodity rows by crawling** — Yeast, Hydrogen Peroxide B.P.,
  Vitamin C (White), Glucose D, Success Methylated Spirit. The Greenbook lists several
  companies under near-identical names (Hydrogen Peroxide: SKG, Ugo Lab, De-Shalom).
  Nothing online identifies which bottle is on the shelf. Only the pharmacy knows.

Bugs fixed, worth knowing:
- **A bare HTTP client gets a blank review card.** `chemironcare.com` answers 403 with
  no `User-Agent` and 200 with a browser one; `_download` turned that into `None` and
  the reviewer saw text with no photo — indistinguishable from a broken bot. Both the
  bot and `approve_candidates.py` now send a browser UA.
- **A root `package.json` silently turns the backend into a Node build.** Merging into
  `main` carried `4d703c3d`'s root `package.json` (playwright, video tooling only) onto
  the branch `web` builds from; Nixpacks switched providers and every container start
  died with `alembic: command not found`. `nixpacks.toml` now pins
  `providers = ["python"]`. `.railwayignore` lists `/package.json` but only filters
  **CLI uploads** — it has no effect on a GitHub-source build.
- Block-bleed paired a caplet photo with a suspension. Block text is trusted only when
  the image has its own heading; NRNs only within 400 chars. **Still live on third-party
  pages**: `dailyneedgroup.com` puts the "DE-DEON'S SYRUP" heading above a *damox*
  photo. Trust the filename over the heading there.
- `pack=<none>` in `match_basis` made Telegram reject the whole review message, so the
  buttons looked dead. Now `pack=(none)` + every interpolation HTML-escaped.
- `_title_for` fell back to stripped markdown, producing names like `)](https://…`.
  Related: many approved candidates still carry marketing copy as `scraped_title`
  ("An Ideal Stool Softener"). Cosmetic, but it makes eyeballing a batch useless.

## 8. Next steps

1. **36 listed products still have no photo**, 16 of them with no manufacturer. This
   is the only photo gap a customer can see. The fastest close is the `📷 Add Photo`
   flow — an afternoon with a phone. Naming the maker for any of the 16 unlocks a
   crawl; that route has by far the best hit rate.
2. **559 draft products ready to create** from 17 crawls. Dry-run only, NOT written.
   `python -m scripts.import_unmatched_products <crawl.json> --manufacturer "<name>" --commit`
   Check a sample of names first — the last two dry runs both surfaced quality problems.
3. **91 products have a photo but are not listed** (mostly Vitabiotics, unpriced).
   Pricing them is what turns those photos into storefront value.
4. **Demo video still paused** — `docs/video/RECORDING-GUIDE.md`; resumes once hero
   products have photos.
5. Untouched issues: `peacewayonline.com.ng` DNS-fails but is hardcoded in
   `app/core/config.py` and `web/public/sitemap.xml`; `app/api/v1/prescriptions.py`
   discards web-uploaded prescription images.
