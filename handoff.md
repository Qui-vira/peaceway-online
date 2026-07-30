# Handoff — product images, and the app-open loader

Written 2026-07-27, updated 2026-07-30. `main` is at `e751db56`, pushed, deployed to
both hosts (Vercel and Railway green), 666 tests pass.

Nothing is unmerged. `refactor/button-system` was merged and shipped on 2026-07-29
(see §9), and the brand loader plus the SEO fixes went out on 2026-07-30 (see §10).

This file now covers two workstreams. §§1-8 are the product-images push, which is still
the live piece of work. §10 is the app-open loader and the search-visibility fixes found
while shipping it; that work is finished and deployed.

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

`docs/PHOTO-CAPTURE-WORKFLOW.md` — the shelf-photo → catalogue-shot pass (§8.1).
Higgsfield MCP is connected and authenticated (checked 2026-07-28: `max` plan, ~1,786
credits). Its tools are served under a long server id, **not** the entry literally
named `higgsfield`, which shows as unauthenticated and is a red herring.

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
   is the only photo gap a customer can see, and it is **in progress**: the owner is
   photographing the packs, then running them through Higgsfield (`gpt_image_2`) in
   Claude Code, using each photo as a reference to produce a clean catalogue shot.

   Everything for that pass — the owner's strict-lock prompt, the shoot list, the
   measured house style, the model settings and the fallbacks — is in
   **`docs/PHOTO-CAPTURE-WORKFLOW.md`**. A reminder is set on `@QuivExecution_Bot`
   for 2026-07-28.

   Two things from that doc that decide whether the output is usable:
   - **`gpt_image_2`'s `quality` defaults to `low`**, which is where pack fine print
     dies. Pass `high`, render at 2k/4k, downscale to the 800px house size.
   - **A generative model redraws text**, and on a pack the text is the strength, the
     NAFDAC number and the pack size. Every output is checked word-by-word against the
     raw photo, and the raw photo is kept as the record. `image_background_remover`
     redraws nothing and is the fallback if the print drifts.

   Naming the maker for any of the 16 also unlocks a crawl; that route had by far the
   best hit rate of anything tried.
2. **559 draft products ready to create** from 17 crawls. Dry-run only, NOT written.
   `python -m scripts.import_unmatched_products <crawl.json> --manufacturer "<name>" --commit`
   Check a sample of names first — the last two dry runs both surfaced quality problems.
3. **91 products have a photo but are not listed** (mostly Vitabiotics, unpriced).
   Pricing them is what turns those photos into storefront value.
4. **Demo video still paused** — `docs/video/RECORDING-GUIDE.md`; resumes once hero
   products have photos.
5. Untouched issue: `app/api/v1/prescriptions.py` discards web-uploaded prescription
   images. (The `peacewayonline.com.ng` hardcoding is **fixed** — see §10. One mention
   survives in `app/core/config.py:103`, inside a comment showing CORS value format,
   with no runtime effect.)

## 9. Shipped: `refactor/button-system`

**Merged and deployed 2026-07-29** as part of the push to `458cdd07`. Kept here because
the CSS-layering lesson below generalises and has not been acted on.

Eight commits, fast-forwarded into `main` with no conflicts. `main` had been failing
lint on its own before this landed; the fix is in this batch.

    4aa3f558  chore(web): silence no-img-element with the reason, not with next/image
    20e93656  docs: record the unmerged button-system branch and what merging it moves
    58a63dd8  docs: tell agents to query the knowledge graph first
    b705812f  refactor(web): replace hand-rolled buttons with the sanctioned components
    c78373c4  docs(design): document the two sanctioned button components
    8b3693bf  fix(ui): layer .pw-btn so documented class overrides actually apply
    f703adb5  chore: ignore local tool state and generated slide renders

### What it changes on screen

`8b3693bf` is the one to read before merging. `.pw-btn*` was emitted *after*
`@tailwind utilities` at equal specificity, so it silently won every collision: a
`min-h-[52px]` on a `.pw-btn` resolved to 48px and nothing errored. DESIGN.md tells
contributors to override with a class rather than a `style` prop — that rule was
simply untrue. Wrapping the block in `@layer components` makes it true, and in doing
so lets ~25 previously inert call-site utilities take effect at once:

| | |
|---|---|
| 5 heights restored to 52px | start ×2, profile, request, reminders/new |
| 13 admin/partner padding sites | `0 24px` → `8px 16px` (3 of them `6px 12px`) |
| 3 admin font sizes | 14px → 12px via `text-xs` |
| 9 disabled opacities | 0.55 → the call site's 0.40 / 0.50 / 0.60 |
| disabled cursor | now `not-allowed`, which it always claimed to be |

The disabled-opacity shifts are disabled-state only; resting appearance is unchanged.
All of it was measured against computed styles in a browser, not read off the source.

`font-semibold` and `disabled:opacity-50` were moved out of `Button`'s shared class
string into the `ghost` and `danger` variants — those two have no `.pw-btn` class to
inherit weight and dimming from. Left in the shared string they would have overridden
`.pw-btn`'s own `font-weight:700` and `opacity:.55` on all 17 `Button` call sites.

**The lesson generalises: this repo's `.pw-btn*` was not the only unlayered block.**
Any bare class written after `@tailwind utilities` in `globals.css` beats the
utilities and fails silently, with no error and no visual warning. `.pw-tile*` sits in
the same file under the same conditions and has not been audited.

### Notes carried over from that branch

- ~~`npm run lint` fails~~ **fixed in `4aa3f558`.** It had been failing on `main`
  since `1f459897` on 2 `@next/next/no-img-element` warnings against
  `--max-warnings=0` — invisible unless you ran lint, because typecheck and build
  both passed. Resolved with an eslint-disable carrying the reason, not `next/image`:
  `file_storage` already serves 800px WebP with EXIF stripped, the client never
  receives intrinsic dimensions (`MediaAsset` has width/height but the API returns
  only `image_url`, and a long-edge cap means the aspect varies), and `mediaSrc()`
  points at the API host so it would need `images.remotePatterns` plus per-image
  Vercel billing to re-encode an already-normalized asset. `fill` would have worked
  around the missing dimensions — both sites render into fixed containers with
  `object-cover` — but it changes layout mechanics for an optimization these images
  do not need. Rendering is unchanged; the commit is comments only.
- **8 files still untracked**: `presentations/build-01..06.js`, `package.json`,
  `package-lock.json`. `.gitignore` now permits exactly these and excludes the
  renders; nothing has added them yet.
- **The slide renders are not reproducible.** The six build scripts emit `.pptx` only.
  `04-wholesalers.pptx`, the six PDFs and the 89 jpg/png renders have **no generator
  in this repo**, and the scripts hardcode `C:\Projects\peaceway-online\presentations\`
  so they only run from that absolute path. They are ignored, so a fresh clone will
  not have them and cannot rebuild them.

## 10. Shipped: the app-open loader, and the SEO defects it uncovered

All deployed 2026-07-30. `main` at `e751db56`. Vercel and Railway both green; typecheck,
lint and production build all pass.

Started as "add the commissioned logo animation as an app loader". Verifying the deploy
turned up several things that were quietly suppressing the site in search, which is most
of what this section is about.

### 10.1 The loader

`web/components/brand/app-loader.tsx`, mounted in `app/layout.tsx`. Plays the client's
Higgsfield animation full-screen, once, then resolves into the app.

**Server-rendered, and that is the point.** An effect-mounted overlay let the page paint
first and dropped the loader on top a frame later — a visible flash of the real app
before the brand moment. Being in the SSR HTML puts it in the first painted frame. The
page still renders behind it, so it does not delay the page's own paint.

That choice is paid for in two places, and both must survive any refactor:

- **No JS at all** — a CSS-only backstop animation retires the overlay. `.js-ready`
  cancels it the instant React mounts, so the animation and the JS transitions never
  fight over `opacity`. Without the backstop, a server-rendered overlay with dead
  scripting is a permanently blank site.
- **Skip-on-return** — a blocking inline script in `<head>` reads `sessionStorage` and
  adds `pw-loader-skip` to `<html>` before first paint. It has to be pre-paint and
  pre-React, which is why it is a raw `<script>` and not the component's job. It is only
  emitted when `LOADER_SCOPE` actually gates replays, and it imports the constant so the
  two cannot drift.

Five independent exits: video end, a 6s hard cap, a stall watchdog (a video frozen at 1s
would otherwise hold the screen for the whole cap), tap or Escape, and the CSS backstop.

`LOADER_SCOPE` defaults to `"every-app-open"`. The tighter `"first-visit-per-session"`
gate is implemented and tested but **not** the default, deliberately: it hid the loader
twice during the build and both times read as "the animation is gone". A brand moment you
cannot reliably see is worse than one seen slightly too often. Note that neither setting
replays on client-side navigation — the component lives in the root layout, which
survives routing and never re-mounts. Only crossing between the marketing site and the
app (a real document load) replays it.

**The asset.** Delivered at 40.7 MB, 1920x1080, 46 Mbps, 7.04s — with content occupying
only the middle 50% of the frame, so on a phone the logo rendered ~195px wide adrift in
an 844px field. Trimmed to 5.0s (the last 2.17s was a static hold), cropped to
`1080x990` around the content's true extent **across the whole 5s** — not the final
frame, or elements flying in from the margins clip — and re-encoded:

    peaceway-loader.webm         183 KB   VP9 CRF 34
    peaceway-loader.mp4          231 KB   H.264 CRF 24, faststart
    peaceway-loader-poster.webp   20 KB   final frame, also the never-blank fallback
    peaceway-loader-mark.webp     85 KB   transparent cut-out, the travelling element

To regenerate after a re-render, the ffmpeg crop is `crop=1080:990:413:64` against the
original 1920x1080 source. If the crop changes, `LOCKUP` in `app-loader.tsx` must be
re-measured — it is the lockup's position as fractions of the delivered frame, and the
handoff geometry is derived from it.

**The exit.** On finishing, the transparent cut-out is laid exactly where the video drew
the lockup (imperceptible swap) and travels to the app's own header logo while the ground
resolves from the animation's `#F3F3F3` to the app's `#0b0c09`. Without that the loader
ends and the app begins across a 17.7:1 luminance flip with nothing carried over, which
is what made it read as a title card in front of the product rather than the product
opening. Routes with no header logo take the plain fade rather than an invented target.

Two traps, both hit and both fixed, worth knowing before editing this:

- The render condition must include the `leaving` phase. Without it React falls back to
  the `<video>` branch the moment the fade begins, remounting the video and snapping the
  logo to full size at the worst possible instant.
- The travelling element must mount at identity and receive its transform on a **later**
  frame. Given the final transform at mount there is nothing to animate from, and the
  logo teleports.

**The ground colour is set inline, not by the `.pw-loader.is-handoff` class.** The class
is in the shipped CSS, correctly ordered, at the right specificity, and it resolves to
`#0b0c09` in a dev build — and it still did not repaint in production. Rather than keep
hunting the cascade, the handoff assigns the colour inline, which wins unconditionally.
The class remains as the no-JS path. If you ever need to debug that: the stylesheet is
cross-origin to the apex host so `cssRules` is unreadable from the page, and a browser
pane that is not compositing freezes transitions while timers keep firing — both produced
convincing false readings during this work.

### 10.2 Removed, because the loader replaces them

- **The route curtain.** A branded full-screen interstitial used to sweep the viewport on
  every navigation. It fired dozens of times per session, where motion reads as latency
  rather than craft. `app/template.tsx` is back to the 180ms `.pw-route` fade and nothing
  else. Do not re-add it; the brand moment belongs on app open, where it happens once.
- **`components/app/peaceway-loader.tsx`.** The data-loading state was a full-screen
  overlay of the logo mark, pinned over the viewport, hiding the header and bottom nav
  behind a brand moment the user saw seconds earlier on the splash. `Spinner` in
  `components/app/ui.tsx` (11 call sites) now renders a skeleton stack in the flow. A
  skeleton answers "what am I waiting for"; a logo only answers "whose app is this".
- **The vector splash system** — `brand-splash.tsx`, `splash-stage.tsx`,
  `peaceway-logo.tsx`, `peaceway-logo-paths.ts`, `peaceway-mark.tsx` and the two
  `/brand-preview` dev routes. Recoverable from git history if wanted: it included a
  potrace vector trace of the logo verified at **IoU 0.956** against the source raster,
  with the script-letter join positions measured from the wordmark's column-density
  profile. `scripts/trace_logo.py` (untracked) regenerates it.

### 10.3 The SEO defects — the part that mattered most

Found while verifying the deploy, all pre-existing, all fixed.

1. **`metadataBase` pointed at `https://peacewayonline.com.ng`, a domain with no DNS at
   all** (`curl` returns 000). Every canonical tag and every OpenGraph image URL the site
   emitted was therefore unreachable. The live host is `www.peacewayonline.com` — the
   apex 308-redirects to it, so `www` is what canonicals must name. The origin now lives
   in `siteConfig.url` (`web/lib/constants.ts`) and `metadataBase` reads it.
2. **`robots.txt` and `sitemap.xml` named the same dead domain.** A `Sitemap:` directive
   on unreachable DNS means a crawler cannot fetch the sitemap at all.
3. **The sitemap listed one URL.** Now generated from the routes — `web/app/sitemap.ts`,
   258 URLs, revalidating hourly so a new medicine appears without a deploy. The static
   `public/sitemap.xml` had to be deleted: a file in `public/` is served directly and
   shadows the generated route.

   Note for anyone extending it: "returns 200" is **not** a usable test for what belongs
   in a sitemap here. Every route answers 200 anonymously because they are client-rendered
   shells whose guest wall appears only after hydration. Personal surfaces, staff
   surfaces, `/offline` and `/showcase` are excluded on judgement, not status code.
4. **All 250 product pages served the root layout's title.** `/shop/[id]` was a client
   component, so `generateMetadata` could not run. 250 pages sharing one title is
   duplicate content, which is why they were initially kept out of the sitemap.

### 10.4 Product slugs and metadata

`/shop/[id]` became `/shop/[slug]`, split into a server component (`page.tsx`, owning
`generateMetadata`) around the interactive client part (`product-detail.tsx`).

URLs went from `/shop/4094c822-8450-4cfc-b330-f46a304d95d3` to
`/shop/afrab-loratadine-tablets-10-mg-3bf9718c`. Old UUID URLs still resolve and **308**
to the slug, so bookmarks and anything already indexed transfer rather than competing.

**No database change.** There is no `slug` column and adding one means an Alembic
migration plus a backfill against production. Slugs are derived from name + strength and
resolved by matching the catalogue, which is 250 items in one ~90KB response, fetched
server-side via `INTERNAL_API_URL` (not `NEXT_PUBLIC_API_URL` — a server component cannot
fetch the relative `/api/v1` proxy path the browser uses) and cached for an hour.

**The 8-character id suffix is unconditional**, and measured against the live catalogue
there are currently **zero** base-slug collisions, so it is redundant today. It stays
because suffixing only on collision requires the whole catalogue to build a link, and the
pages that render product links hold a *filtered* list — two products would silently
share a URL and both 404. Validated across all 250: 250 unique slugs, none unusable.

`fetchCatalog` swallows its own errors and returns `[]`, so an unreachable backend
degrades the sitemap to its 8 static routes and the product page to the client's own
fetch. It can never fail a build or a render.

### 10.5 Search Console and DNS

Both `peacewayonline.com` and `bigquivdigitals.com` are verified as **Domain** properties
(DNS TXT). Domain properties cover apex, `www`, http and https in one property, which
matters here because the apex redirects to `www`.

Two things that cost time and are worth writing down:

- **A Domain property rejects a relative sitemap path.** It needs the full URL,
  `https://www.peacewayonline.com/sitemap.xml`. Relative paths only work for URL-prefix
  properties.
- **Which control panel a DNS record goes in is a consequence of the nameservers, not a
  choice.** `peacewayonline.com` is on Namecheap BasicDNS (`dns1/dns2.registrar-servers.com`)
  so its records are edited at Namecheap. `bigquivdigitals.com` is on
  `ns1/ns2.vercel-dns.com` so its records are edited in Vercel.

**Incident, resolved.** `bigquivdigitals.com`'s nameservers were switched to Namecheap
BasicDNS, which orphaned everything living only in the Vercel zone: DKIM, DMARC, the
Resend and SES records, BIMI and CAA. Inbound mail still worked, so it was not obvious —
but outbound mail was unsigned and unpoliced. Restored by switching back to Custom DNS
with Vercel's nameservers; all records verified answering again.

The lesson: on a domain serving live mail, the nameserver dropdown is the most
destructive control on the page. Records inside a zone are additive and safe; the
nameservers decide which zone is authoritative at all. `peacewayonline.com` carries the
pharmacy site **and** Zoho MX — do not touch its nameservers.

Also note `nslookup` on this machine cannot query CAA (`unknown query type: CAA`) and
`dig` is not installed, which produced a false "CAA missing" reading during the incident.
Use PowerShell's `Resolve-DnsName -Type CAA` or a web tool.

### 10.6 Open items

1. **The loader opens on `#F3F3F3` against the app's `#0b0c09`.** This is an approved
   exception to the dark base that `docs`/PRODUCT.md calls settled, not an oversight: it
   matches the supplied animation, and the owner chose it over re-rendering. The ground
   transition bridges the flip rather than removing it. **If the animation is ever
   re-rendered on `#0b0c09`, this becomes a one-value change** — `--pw-loader-bg` in
   `globals.css` plus swapping the two video files. `APP_GROUND` in `app-loader.tsx`
   would then be redundant.
2. **Indexing lag.** 250 new URLs will take days to weeks and Google will not necessarily
   accept all of them. The sitemap reads **Success**; its "discovered pages" count lagged
   at 8 because Google read a cached copy from before the product deploy. Check **Pages**
   in Search Console in a week to see what was actually accepted.
3. **`/impeccable audit` scored 13/20** ("acceptable, significant work needed") against
   the brand-motion work. The two live findings were the light loader ground
   (item 1) and the client-bundle cost of the vector logo path data — the latter
   is resolved, since that system was deleted in §10.2. The remaining ~50 detector advisories in
   `globals.css` are colour, radius and font-size values predating this work.
4. **Product pages could go further.** Slugs and metadata are in; structured data
   (`Product` / `Offer` JSON-LD, price and availability) is not, and for a
   pharmacy that is what produces rich results. The obvious next SEO step.
