# Workflow — shelf photos → clean catalogue shots

Owner instruction, 2026-07-27 (voice note, corrected by the owner in writing):

> Go to Peaceway, take all the pictures of Peaceway drugs, write a prompt for Claude.
> The purpose is to get a **clean clear picture of the drug photo via Higgsfield in
> Claude Code MCP**. Claude **must not modify the photo** — it must **use the uploaded
> images as reference images**. Claude works on them one by one, simultaneously, and
> each one comes out like the Vitabiotics photo: clean and clear.

An earlier draft of this file was written from a machine transcription that got the
job wrong (it had Claude reading manufacturer names off packs). This version follows
the owner's written correction. The Whisper transcript is not reliable here.

## The target look

Measured from a shipped Vitabiotics image (`Feroglobin Capsules`):

| | |
|---|---|
| Canvas | 800 × 800 |
| Background | pure white `#FFFFFF` to the edges |
| Pack | centred, front-on, filling most of the frame |
| Under the pack | soft mirror reflection |
| Every word on the pack | legible — brand, strength, ingredients, pack size |

That last row is the acceptance test. If a word is less readable after processing
than it was in the raw photo, the output is rejected.

## STRICT LOCK — carry these into every prompt, verbatim

    STRICT LOCK, HIGH IMPORTANCE:
    - Do not do anything I did not ask for.
    - Use the uploaded image as a REFERENCE image. Do not modify the photo.
    - Preserve all the drugs. Every pack in the frame stays, unchanged.
    - Do not turn this image into a cartoon.
    - Do not change the face.
    - The image must feel raw, effortless and genuine — like an unposed everyday
      photo in available light. No heavy editing, no beauty filters, no excessive
      retouching.

("Do not change the face" is inherited from the owner's portrait prompt. It is kept
word for word deliberately — the lock list is the owner's, not ours to trim.)

## Read this before choosing a tool

**A generative model redraws pixels, including text.** On a medicine pack the text is
the safety-critical part: strength, NAFDAC number, pack size. A reference-guided
generation can silently produce `250 mg` where the pack says `125 mg`, and it will
look perfectly clean while being wrong. That is the same class of failure as the
borrowed-strength bug in `handoff.md` §5 — plausible, tidy, and wrong.

So the order of preference is:

1. **Background removal + white composite.** `remove_background`, then centre the
   cutout on an 800×800 white canvas. The pack's own pixels survive untouched. This
   alone produces the Vitabiotics look and satisfies "do not modify the photo".
2. **Upscale**, only if the shot is genuinely low-resolution. Check the pack text
   after: some upscalers redraw small type.
3. **Reference-guided generation** — only if 1 and 2 cannot deliver, and only with
   the STRICT LOCK above, and only if a human compares the output against the raw
   photo word by word before it goes near the catalogue.

Whichever route: **the raw photo is the record.** Keep it. If the processed version is
ever in doubt, the raw file settles it.

## The pass

**1. Shoot** (owner does this). One product per photo, front of pack, whole pack in
frame, no crop. Plain surface, daylight, no flash on foil or gloss. Re-shoot rather
than accept a blurred label — a sharp raw photo makes every later step easier.

**2. Hand the folder to Claude Code** with Higgsfield MCP available. Note: the
Higgsfield server needs to be authorised before its tools can be called at all.

**3. The prompt.**

> For each image in this folder, independently and in parallel:
> produce a clean, clear catalogue photograph of the product, matching this house
> style: 800×800, pure white background, pack centred and front-on, soft reflection
> beneath, every word on the pack fully legible.
>
> Use the uploaded image as a **reference image only**. Prefer background removal and
> a white composite over generating a new image. Never redraw or re-letter anything
> printed on the pack — brand, strength, NAFDAC number and pack size must come
> through pixel-identical to the source.
>
> [STRICT LOCK block, verbatim, here]
>
> Return, per image: the output file, the source file it came from, and any word on
> the pack you cannot read clearly in the result.

**4. Check before it ships.** Put the raw photo and the output side by side. Confirm
brand, strength, pack size and NAFDAC number read identically. Anything altered is a
reject, not a touch-up.

**5. Publish** through the `📷 Add Photo` flow in Telegram, or as an `image_candidate`
for review. Nothing may set `products.image_id` directly — that gate is the whole
reason no wrong pack has reached the storefront.

## What this closes

36 listed products still have no photo — the only photo gap a customer can see.
(8,461 other photoless products are unlisted; nobody sees them.) Scraping is finished
as a source: `handoff.md` §6 records the ceiling and why.

### Shoot list — 36 listed products with no photo

Snapshot from production, 2026-07-27. Regenerate by selecting listed products with
`image_id IS NULL`.

- [ ] Afrab Oral Rehydration Salt
- [ ] Alben Vitamin C Caplet 1000 mg
- [ ] Alben Zinc Sulphate Tablet 50 mg
- [ ] Alkum Cough Expectorant (non Drowsy)
- [ ] Astymin
- [ ] Benzyl Benzoate Lotion
- [ ] Cal D3 Tablet
- [ ] Calamine Lotion BP
- [ ] Chemiron Blood Tonic Iron+
- [ ] CIPMED-500 (Ciprofloxacin Tablets USP)
- [ ] Daily Multivitamin
- [ ] Danacid
- [ ] Dr. Fizzo Lemon Flavour
- [ ] Dr. Fizzo Orange Flavour
- [ ] Durex Feel Condoms
- [ ] Durex Fetherlite Condoms
- [ ] Fineappeti Forte Syrup
- [ ] Glucose D
- [ ] HS 12
- [ ] Hydrogen Peroxide B.P.
- [ ] IBUCAP Sachet
- [ ] JTL Plaster
- [ ] Liquid Iron (Adler)
- [ ] Meritamin
- [ ] MIM Health & Vitality Tonic
- [ ] MOKO Bicarbonate of Soda B.P.
- [ ] Nutracid
- [ ] Orheptal
- [ ] Relcer Gel
- [ ] Ruzu Herbal Bitters
- [ ] Success Methylated Spirit
- [ ] Sumo Active
- [ ] Tuxil-D Expectorant for Adults
- [ ] Vitamin C Chewable
- [ ] Vitamin C (White)
- [ ] Yeast

Four of these have a candidate queued that cannot be fetched at all, because the
manufacturer's own TLS certificate is expired or incomplete (`handoff.md` §6):
Astymin, IBUCAP Sachet and two others. A shelf photo replaces them outright.

While the packs are in hand, 16 of these also have no manufacturer recorded and it is
printed on the pack — worth noting down, but it is a separate write from the photo and
must not be inferred from the image by a model.
