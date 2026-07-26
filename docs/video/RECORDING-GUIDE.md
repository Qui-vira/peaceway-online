# Peaceway Online — Demo Video Recording Guide

> ## ⏸ STATUS: PAUSED — 2026-07-26
>
> **Blocked on:** real product photography.
>
> `/shop` rendered dosage-form SVG icons because `products` had no image column. The
> product grid is the centrepiece of the demo, so filming it with placeholder icons
> undercuts the whole video.
>
> **The mechanism is LIVE** — built and deployed 2026-07-26. In the Telegram Products
> menu, open a product → `📷 Add Photo` → send one photo of that pack. It is stripped of
> EXIF (phone GPS never reaches the public site), downscaled to 800px, converted to WebP
> (~60 KB) and appears on `/shop` immediately. Products without a photo keep their SVG
> icon, so nothing regressed.
>
> **Resume condition — one step left:**
> Photograph the ~9 hero products listed under *Confirmed-good products* below, using
> the Telegram flow. Verified live: all routes 200, `image_url` present on every catalog
> row, `/api/v1/media/{id}` serving.
>
> **Do not start recording until those land.** Everything else stays valid — the shot
> lists, the live-URL table and the Telegram instructions were all verified 2026-07-26.

**Target:** 60–90s full demo walkthrough, 16:9, 1920×1080
**Rule:** every frame showing the product is real captured footage. Nothing about the
interface is AI-generated.

---

## Verified live surfaces

Checked 2026-07-26:

| Surface | URL | Status |
|---|---|---|
| Webapp | `https://www.peacewayonline.com` | 200 OK |
| Webapp apex | `https://peacewayonline.com` | 308 → `www.` |
| Telegram bot | `https://t.me/Peacewayonline_bot` | live |
| Telegram channel | `https://t.me/peacewayonline` | live |
| Backend health | `https://web-production-35e301.up.railway.app/health` | 200 OK |
| `peacewayonline.com.ng` | — | **DNS FAILS** — do not film, do not put on screen |

> `peacewayonline.com.ng` is hardcoded in `app/core/config.py:103` and
> `web/public/sitemap.xml`. It does not resolve. Fix separately; keep it out of the video.

---

## PART A — Website (I record this)

Recorded headlessly with Playwright at 1920×1080, 30fps, with a synthetic cursor
overlay and human-paced dwell times. You review the raw capture before any
motion design is applied.

### Shot list — real pages, confirmed to exist in `web/app/`

Revised after the discovery pass on 2026-07-26 (`node scripts/video/discover.mjs`).
All routes below returned HTTP 200 and rendered real content.

| # | Page | Route | What happens on screen | ~sec |
|---|---|---|---|---|
| A1 | Landing | `/` | Load, settle, slow scroll through hero | 6 |
| A2 | Landing CTA | `/` | Cursor moves to the real "ORDER ON TELEGRAM" CTA, hovers | 3 |
| A3 | Shop | `/shop` | Real catalog grid — 51 products, real ₦ prices | 5 |
| A4 | Search | `/shop` | Type a real product name, results filter live | 6 |
| A5 | Product | `/shop/[id]` | Open one real product, price + details visible | 5 |
| A6 | Cart | `/cart` | Item added, cart total renders | 4 |
| A7 | Checkout | `/checkout` | Delivery area picker, real fee appears | 6 |
| A9 | Prescription | `/prescription` | Prescription upload screen | 4 |

### Cut shots — and why

| # | Route | Reason |
|---|---|---|
| ~~A8~~ | `/ask-pharmacist` | Renders **"Create your profile first"**, not the form. Shown on the Telegram side instead, where you're already authenticated. |
| ~~A10~~ | `/orders` | Same profile gate. Order tracking is covered by Telegram shot B-track. |

`/request` and `/start` are gated the same way. Not filmed.

### ⚠️ Keep these products out of frame

These render **₦0** with a live "Add" button on the production storefront:
Astymin 200ml, Benzyl Benzoate Lotion 100ml, Calamine Lotion 100ml,
Calamine Lotion BP 100ml, Canderm Dusting Powder 50g, Broncholyte 4mg/5ml.

Tracked as a separate bug. Do not let them into a shot.

### Confirmed-good products for the search/product shots

Real names, real prices, verified live 2026-07-26:

| Product | Price |
|---|---|
| Afrabvite Multivitamin Drops | ₦1,500 |
| Cal D3 Tablet 1250 mg; 250 IU | ₦1,300 |
| Alben Zinc Sulphate Tablet 50 mg | ₦750 |
| Alben Vitamin C Caplet 1000 mg | ₦700 |
| Afrab Loratadine Syrup 5 mg/5 mL | ₦600 |
| Alkum Cough Expectorant (non-drowsy) | ₦600 |
| AC-Ibu 200 Tablet 200 mg | ₦500 |
| Afrab Oral Rehydration Salt 20.5 g | ₦400 |
| AC-Drex Tablet 500 mg; 30 mg | ₦350 |

**Rules I follow while recording:**
- No fake data typed into any field. If a form needs input, we use a real test
  order and I tell you exactly what was entered.
- No page is filmed if it errors or renders empty. It gets cut, and I report it.
- Every dwell is ≥1.2s so a viewer can actually read the screen.
- Cursor moves are eased, not teleported.

**If a page is broken or empty, I do not fake it.** I report it and we either fix it
first or drop the shot.

---

## PART B — Telegram bot (you record this)

I cannot log into Telegram. This part is yours. It takes about 10 minutes.

### Setup — do this first

1. **Use Telegram Desktop on Windows, not your phone.** Reason: 16:9 output.
   Phone recording is 9:16 and gets pillarboxed with ugly black bars.
2. Open Telegram Desktop → make the window roughly **1280×720** (it will be
   upscaled cleanly to 1080p). Don't fullscreen it.
3. **Switch to a clean theme** — Settings → Chat Settings → pick the default
   light theme. Dark themes with custom wallpapers make the motion design harder
   to key over.
4. **Hide your other chats:** Settings → Advanced → or simply drag the window
   narrow enough that the chat list is collapsed. Your personal conversations
   must not appear on camera.
5. **Set Telegram zoom to 125%** (Settings → Chat Settings → Interface scale) so
   the text is legible at 1080p.

### Recorder

Use **Xbox Game Bar** — built into your Windows 11, nothing to install:

- Press `Win + G`
- Click the **Capture** widget → record button, or just press `Win + Alt + R`
- Stop with `Win + Alt + R` again
- Files land in `C:\Users\Bigquiv\Videos\Captures\`

If Game Bar refuses to record Telegram (it sometimes blocks non-game windows),
use **OBS Studio** with a Window Capture source instead. Tell me and I'll walk
you through the OBS setup.

### Shot list — real buttons, pulled from `app/bot/keyboards/customer.py`

Record these as **one continuous take** if you can. If you fumble, just pause 3
seconds and redo that step — I'll cut it out.

| # | Action | What must be visible | ~sec |
|---|---|---|---|
| B1 | Send `/start` | The welcome message + the full main menu keyboard | 5 |
| B2 | Pause on the menu | All 9 buttons readable: `🛒 Order Medicine`, `💬 Ask Pharmacist`, `📍 Delivery Areas`, `⭐ Popular Products`, `👨‍⚕️ Speak to Support`, `📦 Track Order`, `📋 How It Works`, `👤 My Profile`, `📝 Track My Requests` | 3 |
| B3 | Tap `🛒 Order Medicine` | `🔎 Search by name` / `🗂 Browse categories` / `🧺 View cart` | 4 |
| B4 | Tap `🔎 Search by name`, type a real medicine | Real search results with real prices | 6 |
| B5 | Open one result | Product card + `🧺 View Cart` + `💬 Ask Pharmacist` | 5 |
| B6 | Add to cart → `🧺 View Cart` | Cart with `✅ Checkout` / `🗑 Clear cart` / `➕ Add more` | 4 |
| B7 | Tap `✅ Checkout` | The delivery detail prompts, step by step | 6 |
| B8 | Reach the payment chooser | `🏦 Bank Transfer` / `📤 Upload Proof of Payment` — **STOP HERE.** Do not tap `✅ Confirm Order`. | 5 |
| B9 | Back to menu → `📋 How It Works` | The 5-step How It Works message | 4 |
| B10 | `⭐ Popular Products` | The real listed, priced, in-stock items | 4 |

### Hard rules for your recording

> ### ⛔ DO NOT CONFIRM THE ORDER
>
> **Decided 2026-07-26.** Walk the flow all the way to the payment chooser
> (`🏦 Bank Transfer`), then stop. **Never tap `✅ Confirm Order`** in
> `app/bot/customer/checkout.py:189`.
>
> Why: the bot runs in webhook mode against the **production** Railway Postgres.
> Confirming writes a real order row and fires staff alert DMs + emails.
>
> The footage loses nothing — the payment chooser is the natural last beat of the
> demo anyway, and the closing shot is the website CTA, not an order receipt.

- **Real-looking details, real flow.** Do not type placeholder junk like
  "test test 123" into the address field — it will be on screen and it looks fake.
  Use your own name and a real Lagos address.
- **Do not show a real customer's data.** Use your own details or a clearly-yours
  test account.
- **Do not show the admin/staff menus** unless you want them in the video. Record
  as a customer.
- **Scroll slowly.** Fast scrolling turns to mush at 30fps.
- **Let each screen sit for 2 full seconds** after it loads before you tap the next
  thing. Dead air is easy to cut; missing frames are not.
- If a button does nothing or errors — **stop and tell me**. That's a bug, and it
  goes in the fix list, not the video.

### Hand it off

Drop the file anywhere and give me the path. Examples:
`C:\Users\Bigquiv\Videos\Captures\Telegram 2026-07-26.mp4`

I'll transcode, cut, and frame it. You review the cut before any motion design lands.

---

## PART C — What I need from you before recording starts

1. **One real product name** that is actually priced and in stock, to search for.
   Per the current data only ~8 demo OTC items are priced — I need to know which
   one looks best on camera.
2. **A delivery area** to pick at checkout that has a real fee configured.
3. ~~Confirm the test order is safe to place~~ — **RESOLVED 2026-07-26: no order
   will be confirmed.** Recording stops at the payment chooser. Nothing is written
   to the production database.
4. **Say what the video claims.** Any number, promise, or delivery time that
   appears as on-screen text must be one you can stand behind. I will write the
   script with `[PLACEHOLDER]` markers for anything I cannot verify from the
   codebase, and I will not fill them in myself.

---

## Approval gates — you sign off at each one

1. ☐ This guide — approve the shot lists
2. ☐ Raw website capture — you watch it, approve or re-shoot
3. ☐ Your Telegram capture — I confirm it's usable
4. ☐ Script + on-screen text — placeholders resolved by you
5. ☐ Rough cut, no motion design — pacing approved
6. ☐ Motion design pass — the real work
7. ☐ Voiceover + music
8. ☐ Final 1080p master
