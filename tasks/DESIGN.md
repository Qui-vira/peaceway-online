# PeaceWay — DESIGN.md (single source of truth)

Reconciles the existing app brand (`web/app/globals.css`) with the UI/UX Pro Max generated system
(`design-system/peaceway/MASTER.md`). Where they conflict, **brand identity wins; Pro Max's
accessibility/structure discipline is adopted.**

## Reconciliation summary

| Dimension | Existing brand | Pro Max suggested | DECISION |
|---|---|---|---|
| Theme mode | Dark cinematic `#0b0c09` | Light `#F0FDF4` | **Keep DARK.** Reject light. Brand is established, premium. |
| Primary green | `#0f673c` (`--g`) | `#15803D` / `#22C55E` | **Keep `--g` for fills; use brighter greens for text/icons/focus** (contrast — see below). |
| Accent | Red `#a80b16` (`--r`) | Trust blue `#0369A1` | **Keep red.** Blue optional trust element only if a badge needs it later. |
| Type | Syne + DM Sans | Lexend + Source Sans 3 | **Keep Syne + DM Sans.** Brand consistency. |
| Spacing/shadow | ad-hoc | 4/8/16/24/32/48/64 scale | **Adopt the scale** (formalize into tokens). |
| Semantic tokens | raw CSS vars | `--color-primary` etc. | **Adopt a semantic layer** mapping onto existing vars. |
| A11y (focus, 44px, contrast, reduced-motion) | partial (reduced-motion ✓) | strong | **Adopt fully.** |
| Motion | GSAP available | page-transition + Standard tier | **Adopt patterns** for scroll sequence + transitions. |

## ⚠️ Accessibility fix (must apply during rebuild)
On the dark base `#0b0c09`, the primary green `--g #0f673c` **fails WCAG AA (4.5:1)** for text and small
icons. Rule: **`--g` is for fills/borders/large shapes only.** For any green **text, small icon, or focus
ring**, use the bright ramp (`#34d98a` / `#4ade80`) which passes AA on dark. (The mobile CSS already does
this — we formalize it.)

## Color tokens (dark theme)
Existing raw vars stay; add a semantic layer on top.

```css
:root {
  /* --- existing brand primitives (unchanged) --- */
  --g: #0f673c;      /* green - FILLS / borders / large shapes only */
  --g2: #1a8a50;     /* brighter green - interactive fills, hover */
  --g-on: #34d98a;   /* NEW: bright green for text/icon/focus on dark (AA-safe) */
  --r: #a80b16;      /* red accent */
  --t: #dcdddb;      /* primary text  (AA on dark) */
  --m: #b1bdb0;      /* muted text    (AA-large / secondary) */
  --bg: #191a17;     /* raised surface */
  --bgd: #0b0c09;    /* page background */
  --bdr: rgba(255,255,255,.08);
  --bdr2: rgba(255,255,255,.04);

  /* --- semantic layer (Pro Max structure, mapped to brand) --- */
  --color-primary:      var(--g2);
  --color-on-primary:   #ffffff;
  --color-accent:       var(--r);
  --color-background:   var(--bgd);
  --color-surface:      var(--bg);
  --color-foreground:   var(--t);
  --color-muted:        var(--m);
  --color-border:       var(--bdr);
  --color-focus:        var(--g-on);
  --color-destructive:  var(--r);
  --color-success:      var(--g-on);
}
```

## Typography
- **Display/headings:** Syne (`--font-syne`), weights 700/800, tracking `-0.02em`.
- **Body/UI:** DM Sans (`--font-dm-sans`), 400/500/600.
- **Scale (px):** 11 · 12 · 13 · 14 · 16(base) · 19 · 24 · 32 · 46 · 76(hero, `clamp`).
- **Body min 16px** on mobile inputs (prevents iOS auto-zoom). Line-height 1.5–1.75.

## Spacing scale (formalize)
`--space-xs 4` · `-sm 8` · `-md 16` · `-lg 24` · `-xl 32` · `-2xl 48` · `-3xl 64`. Use for all new padding/gaps.

## Shadow scale (dark-tuned)
```css
--shadow-sm: 0 2px 8px rgba(0,0,0,.30);
--shadow-md: 0 8px 24px rgba(0,0,0,.38);
--shadow-lg: 0 16px 44px rgba(0,0,0,.44);
--shadow-glow: 0 0 0 1px rgba(15,103,60,.25), 0 18px 60px rgba(0,0,0,.35); /* existing boxShadow.glow */
```

## Radius
Cards 16px · large cards/panels 20px · pills/buttons 22–32px · inputs 10–12px.

## Component states (adopt)
- **Focus:** visible 3px ring `var(--color-focus)` at ~50% alpha on every interactive element. Never remove.
- **Hover** (pointer only, already gated via `@media (hover:hover)`): 2–4px lift + green glow, 150–300ms.
- **Press** (touch, `@media (hover:none)`): `scale(0.98)`, 120ms.
- **Disabled:** opacity 0.4 + `cursor: not-allowed` + semantic `disabled`.
- **Loading:** skeleton/shimmer for >300ms; buttons show spinner + disabled during async.

## Breakpoints
375 (small phone) · 768 (tablet, current mobile cutover is 800px) · 1024 (sidebar threshold) · 1440.
Container max-width 1240px, gutters 56px desktop / 20px mobile (matches `.con`).

## Motion (Motion dial 7/10 = Standard)
- **Durations:** micro 150–300ms; transitions ≤400ms; exits ~65% of enter.
- **Easing:** ease-out enter, ease-in exit; `cubic-bezier(0.22,0.61,0.36,1)` (already in use).
- **Scroll sequence (hero):** GSAP + ScrollTrigger, pinned canvas, `scrub` to scroll. See Phase 1.
- **Page transition** (optional, from MASTER): overlay `yPercent` timeline, `power2.inOut`, 400ms, mounted at layout root.
- **Always** honor `prefers-reduced-motion` (globals.css already disables anim/transform under it).

## Icons
SVG only — the app already uses `lucide-react`. No emoji as structural icons. One family, consistent stroke.

## Anti-patterns (do NOT use)
Neon colors · AI purple/pink gradients · motion-heavy decoration · emoji icons · layout-shifting hovers ·
low-contrast text · instant (0ms) state changes · invisible focus rings · green `--g` for text/small icons.

## Pre-delivery checklist (dark-adapted)
- [ ] No emoji icons (lucide-react SVG only)
- [ ] `cursor-pointer` on all clickables; 44×44px min touch targets
- [ ] Hover 150–300ms (pointer only); press state on touch
- [ ] **Dark** text contrast: primary ≥4.5:1, secondary ≥3:1 (verify green text uses `--g-on`)
- [ ] Visible 3px focus rings, keyboard nav order = visual order
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive 375/768/1024/1440, no horizontal scroll
- [ ] No content hidden behind fixed nav / safe-area (`env(safe-area-inset-*)`)
```
