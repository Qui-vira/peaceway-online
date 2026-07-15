---
name: Peaceway Online
description: The 24/7 ordering and operations surface for a real, licensed Lagos pharmacy.
colors:
  dispensary-green: "#0f673c"
  dispensary-green-lit: "#1a8a50"
  signal-green: "#34d98a"
  cross-red: "#a80b16"
  counter-black: "#0b0c09"
  raised-surface: "#191a17"
  ink: "#dcdddb"
  ink-muted: "#b1bdb0"
  hairline: "#ffffff14"
typography:
  display:
    fontFamily: "Syne, sans-serif"
    fontSize: "clamp(36px, 5.5vw, 76px)"
    fontWeight: 800
    lineHeight: 0.96
    letterSpacing: "-0.028em"
  headline:
    fontFamily: "Syne, sans-serif"
    fontSize: "34px"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  body:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
  label:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.2em"
rounded:
  input: "12px"
  surface: "16px"
  panel: "20px"
  pill: "32px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  2xl: "48px"
  3xl: "64px"
components:
  button-primary:
    backgroundColor: "{colors.dispensary-green-lit}"
    textColor: "#ffffff"
    rounded: "{rounded.pill}"
    padding: "15px 32px"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "14px 32px"
  button-app:
    backgroundColor: "{colors.dispensary-green-lit}"
    textColor: "#ffffff"
    rounded: "{rounded.surface}"
    padding: "0 24px"
    height: "44px"
  tile:
    backgroundColor: "#ffffff0b"
    textColor: "{colors.ink}"
    rounded: "{rounded.surface}"
    padding: "20px"
---

# Design System: Peaceway Online

## 1. Overview

**Creative North Star: "The Counter at 3AM"**

A real dispensary counter, lit and staffed, while the rest of the street is dark. Every decision in
this system follows from that image. The near-black base (#0b0c09) is night, not fashion. The green
is the lit sign you can see from the road. The calm, unhurried tone is a competent pharmacist who is
simply still open — not a brand performing urgency.

This matters because the product's real adversary is doubt. In a market where counterfeit medicine is
a live fear, the interface either reads as evidence that a licensed pharmacy exists behind it, or it
reads as another reseller. Specificity is how the system argues: a named street, a named delivery
area, a real person answering. Ornament is not part of the argument.

The system is physical rather than flat. Surfaces are objects: a tile carries a solid bottom lip — a
light edge catching the room — and a grounding shadow beneath it, and it depresses when pressed. That
tactility is the personality. It is what keeps a dark interface from reading as a void.

**Key Characteristics:**
- Night-dark base, lit by a single green
- Physical surfaces that respond to touch, not floating cards
- Display type used sparingly and set very tight; DM Sans carries everything else
- Restraint: the accent marks actions and state, never decorates
- Legibility treated as a safety property, not a preference

## 2. Colors

A near-black room with one green light in it, and a red reserved for the cross.

### Primary
- **Dispensary Green** (#0f673c): The signature. Names the place, not the pigment — the green of a
  pharmacy sign, not a startup accent. Carries fills, borders and large shapes: button bodies, tinted
  panels, the hero stage. It is structure, not voice.
- **Dispensary Green, Lit** (#1a8a50): The interactive step. Primary button bodies and hover fills —
  the same green with the light on.
- **Signal Green** (#34d98a): The green that speaks. Every green *word*, small icon, and focus ring.
  Bright enough to survive the dark base.

### Secondary
- **Cross Red** (#a80b16): The pharmacy cross. Destructive actions and genuine problems only. It is
  never a highlight, never a badge for emphasis, never used to draw the eye toward something good.

### Neutral
- **Counter Black** (#0b0c09): The page. The dark street the counter is lit against.
- **Raised Surface** (#191a17): The tier above the page — panels and raised regions.
- **Ink** (#dcdddb): Primary text. Reads at 4.5:1+ on Counter Black.
- **Ink Muted** (#b1bdb0): Secondary and supporting text. Never body copy at small sizes.
- **Hairline** (rgba(255,255,255,0.08)): Borders and dividers. Structure by implication.

### Named Rules

**The Fills-Only Rule.** Dispensary Green (#0f673c) is forbidden on text, small icons and focus
rings. It fails WCAG AA against Counter Black — a legibility failure on a page where the words are
drug names and dosages. Green type uses Signal Green (#34d98a) or #4ade80. No exceptions, and no
"it's only a label."

**The Red Means Stop Rule.** Cross Red never celebrates. If a red element is not an error, a warning
or a destructive action, it is the wrong colour.

**The One Light Rule.** One green light in a dark room. If a screen has green competing with green,
or the accent is doing decorative work, the screen has lost the metaphor.

## 3. Typography

**Display Font:** Syne (fallback: sans-serif) — weights 700/800
**Body Font:** DM Sans (fallback: sans-serif) — weights 300/400/500/600

**Character:** A geometric display against a humanist body — paired on a real contrast axis, not two
sans-serifs pretending to differ. Syne is architectural and set very tight; it is the signage. DM
Sans is the pharmacist's voice: plain, legible, unremarkable on purpose.

### Hierarchy
- **Display** (Syne 800, clamp(36px, 5.5vw, 76px), line-height 0.96, tracking -0.028em): The landing
  hero only. One per page, ever.
- **Headline** (Syne 700, 34px mobile and up, line-height 1.1, tracking -0.02em): Section headings on
  the marketing surface.
- **Title** (DM Sans 600, 19–24px, line-height 1.3): Card and screen titles inside the app. Syne does
  not appear here.
- **Body** (DM Sans 400, 16px, line-height 1.6): All prose. Cap measure at 65–75ch. 16px is a floor
  on mobile inputs, not a preference — smaller triggers iOS auto-zoom.
- **Label** (DM Sans 600, 12px, tracking 0.2em, uppercase): Eyebrows and small caps labels.

### Named Rules

**The Signage-Only Rule.** Syne is signage. It appears on the landing hero and section headings, and
nowhere in the app — not on buttons, labels, table headers or data. A display font in a UI label is
the fastest way to make a tool feel untrustworthy.

**The 16px Floor Rule.** Body and input text never drop below 16px on mobile. This is an
accessibility floor and an iOS zoom guard at once.

## 4. Elevation

This system does not float. Depth is physical: a surface is an object with an edge, sitting on
something, and it moves when you press it. A tile carries a solid bottom lip (a 4px light edge, as if
a raised surface were catching light from the room) over a soft grounding shadow. Press it and it
travels 3px down and the lip collapses to 1px — the object depresses, it does not fade. Tonal
layering supports this (Counter Black #0b0c09 for the page, Raised Surface #191a17 above it), but the
lip is what makes the metaphor legible.

### Shadow Vocabulary
- **Tile lip** (`box-shadow: 0 4px 0 0 rgba(255,255,255,0.05), 0 10px 22px -12px rgba(0,0,0,0.6)`):
  The default raised surface. The first shadow is the edge; the second is the ground.
- **Tile pressed** (`box-shadow: 0 1px 0 0 rgba(255,255,255,0.05), 0 5px 12px -8px rgba(0,0,0,0.6)`):
  Paired with `translateY(3px)`. The object under a finger.
- **Green glow** (`box-shadow: 0 0 0 1px rgba(15,103,60,.25), 0 18px 60px rgba(0,0,0,.35)`): Reserved
  for hover on pointer devices and for elements that are genuinely lit.

### Named Rules

**The Objects-Not-Cards Rule.** If a surface has a drop shadow and no edge, it is floating, and it is
wrong. The lip is the system. A shadow alone is a card from another design system.

**The Press-Is-Physical Rule.** Pressable things depress. Touch feedback is `scale(0.98)` or a 3px
translate within 120–140ms — never a colour flash, never nothing.

## 5. Components

Tactile and confident. Things you can press, that look like they can be pressed, and that behave like
hardware when you do.

### Buttons
- **Shape:** Fully pill on the marketing surface (32px radius); softened rectangle in the app (16px
  radius). Two vocabularies, one per register — never mixed on a screen.
- **Primary:** Dispensary Green Lit (#1a8a50) body, white text, 15px/32px padding, DM Sans 700 at
  14px with 0.06em tracking. On the hero it takes a green gradient (#23bd6a → #0f673c) and a solid
  green lip.
- **Secondary:** Transparent with a 2px hairline border (rgba(220,221,219,0.28)), Ink text, 14px/32px
  padding. Same size and shape as primary; only the weight of the invitation differs.
- **Hover / Focus:** Hover is pointer-only — a 2px lift plus green glow over 150–300ms, gated behind
  `(hover: hover) and (pointer: fine)` so it never sticks on touch. Focus is a visible 3px Signal
  Green ring at ~50% alpha, offset from the surface. It is never removed.
- **App buttons:** 44px minimum height, 16px radius, 24px horizontal padding.

### Tiles / Containers
- **Corner Style:** 16px (surfaces), 20px (large panels).
- **Background:** rgba(255,255,255,0.045) over Counter Black — a lift by transparency, not a fill.
- **Border:** 1px rgba(255,255,255,0.09). Structure by implication.
- **Shadow Strategy:** The tile lip. See Elevation.
- **Internal Padding:** 16–20px (`md`–`lg`).

### Inputs / Fields
- **Style:** 12px radius, hairline border, transparent-to-dark fill, 16px text.
- **Focus:** The same 3px Signal Green ring. Consistent with every other interactive element.
- **Error:** Cross Red border plus a text message. Colour alone never carries meaning.

### Navigation
- **App:** A sticky top bar (h-16) on desktop, a fixed bottom bar on mobile — same five destinations,
  same icons, Signal Green for the active item, muted Ink otherwise. Icons are lucide-react at
  consistent stroke.

### Signature Component: the scroll sequence
The landing hero renders a 121-frame image sequence of the Peaceway building on a canvas, scrubbed to
scroll position via GSAP ScrollTrigger, with the scene pinned across ~190vh. Frames are contain-fit
and subsampled on mobile for payload. It is the one piece of genuine spectacle in the system and it
earns its place by being the argument: the building is real, and here it is.

## 6. Do's and Don'ts

### Do:
- **Do** use Signal Green (#34d98a) for every green word, small icon and focus ring.
- **Do** give every surface an edge. The lip is the system.
- **Do** keep hover behind `(hover: hover) and (pointer: fine)`, and give touch a press state instead.
- **Do** hold body text at 16px minimum, at 4.5:1 or better, with a 65–75ch measure.
- **Do** honour `prefers-reduced-motion` on every animation — motion here is state, not decoration.
- **Do** show a skeleton for anything over 300ms. A spinner in the middle of content is an apology.
- **Do** keep the three auth domains visually distinct. Customer, staff and partner surfaces should
  never be mistaken for one another.

### Don't:
- **Don't** use Dispensary Green (#0f673c) for text or small icons. It fails AA on the dark base.
- **Don't** rebuild this light. PRODUCT.md rejects a "light, clinical, generic-healthcare theme" by
  name, and `tasks/DESIGN.md` rejects a light theme explicitly. The dark base is settled.
- **Don't** reach for a marketplace or discount-pharmacy look — the drop-shipper aesthetic is the
  exact suspicion this product exists to overcome.
- **Don't** put Syne in the app. Display fonts in UI labels, buttons or data are prohibited.
- **Don't** use neon, purple/pink gradients, or gradient text (`background-clip: text`). Emphasis
  comes from weight and size.
- **Don't** use emoji as structural icons. lucide-react SVG only, one family, consistent stroke.
- **Don't** ship a floating card: a drop shadow with no edge belongs to a different system.
- **Don't** use Cross Red for anything that isn't an error, a warning or a destructive action.
- **Don't** animate a section into visibility from a hidden default. If the animation never fires,
  the section ships blank.
- **Don't** let a heading overflow its column. Test the copy at 375px, not just on a desktop.
