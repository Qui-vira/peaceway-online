# Product

## Register

product

## Platform

web

## Users

Three audiences, walled off from each other by design, and all three matter.

Lagos customers are the reason the thing exists: people in Igando, Agodo, Ikotun and the surrounding
areas who need genuine medicine delivered and a pharmacist they can actually ask. They arrive on a
phone, often on mobile data, frequently at an hour when no pharmacy is open. Many reach Peaceway
through Telegram rather than the website.

Peaceway staff run operations from the admin surface: dispatch, sourcing, payment confirmation,
prescriptions. Their work is the difference between an order placed and an order delivered.

Wholesalers and supplier partners use the partner portal to confirm stock and fulfil sourcing
requests when something is not held in-house. Partner auth is a separate domain from staff auth and
must stay that way.

## Product Purpose

Peaceway Online is the 24/7 ordering and pharmacy-operations layer for Peaceway Pharmacy, a real
licensed pharmacy in Lagos. Customers browse, ask, order and track. Staff run fulfilment. Partners
supply what is not in stock. It runs on its own backend and does not depend on PharmaOS at runtime.

Success is not one number. It is four, and they compound: orders completed, trust established (the
antidote to a market where counterfeit medicine is a real fear), fewer manual steps for staff, and
customers who come back for refills and reminders rather than buying once.

## Positioning

A real, licensed Lagos pharmacy you can reach at 3am - with genuine medicine, a pharmacist behind
every answer, and delivery to your area.

## Brand Personality

Established, premium, calm. The tone is a competent pharmacist, not a marketplace: it does not
shout, discount, or oversell. Confidence is conveyed by specificity - a named location, a named
delivery area, a real person answering - rather than by adjectives. The interface should feel like
evidence that the pharmacy exists, because for this audience that is the entire question.

## Anti-references

Not a light, clinical, generic-healthcare theme. The brand is committed to a dark cinematic base
(#0b0c09) and that decision is settled; `tasks/DESIGN.md` explicitly rejects a light rebuild.

Not a marketplace or discount-pharmacy aesthetic. Not anything that reads as a drop-shipper or an
unlicensed reseller - that is precisely the suspicion the product has to overcome.

## Design Principles

Trust is the product. In a market where counterfeit medicine is a live fear, every surface either
adds evidence that this is a real licensed pharmacy or it is decoration. Specificity is the
mechanism: real address, real areas, real pharmacist.

Meet people where they already are. Telegram is a first-class path, not a fallback - the web app and
the bot are two doors into the same pharmacy, and neither is a lesser citizen.

Brand identity outranks generated systems. The visual identity is established and reconciled in
`tasks/DESIGN.md`; where a generic design system disagrees with it, the brand wins and the system's
accessibility discipline is adopted.

Legibility is not negotiable on a dark base. The primary green `--g #0f673c` fails AA for text on
#0b0c09 and is for fills and large shapes only; text, small icons and focus rings use the bright
ramp (#34d98a / #4ade80).

Three doors, three locks. Customers, staff and partners are separate auth domains. Convenience is
never a reason to merge them.

## Accessibility & Inclusion

WCAG 2.1 AA, already the committed standard in `tasks/DESIGN.md` rather than an aspiration: 4.5:1
for body text, a visible 3px focus ring on every interactive element, 44px minimum touch targets,
and honoured `prefers-reduced-motion` across the motion system.

Assume a phone, mobile data, and a wide range of Android devices. Payload and perceived speed are
accessibility concerns here, not just performance ones.
