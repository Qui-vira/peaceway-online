export const siteConfig = {
  name: "Peaceway Online",
  /**
   * The canonical origin, and the base every absolute URL in the metadata is
   * resolved against.
   *
   * `www` is not cosmetic here: the apex 308-redirects to it, so `www` is the
   * host that actually serves the site and therefore the one canonical tags and
   * OG images must point at.
   *
   * This was `https://peacewayonline.com.ng` until 2026-07-29 - a domain that
   * does not resolve at all. Every canonical tag, every OG image URL and the
   * sitemap were pointing at dead DNS, so nothing that crawls or unfurls the
   * site could reach the referenced pages or preview images.
   */
  url: "https://www.peacewayonline.com",
  /**
   * Positioning: the product is the pharmacy, not the delivery.
   *
   * Title and description used to lead with "Lagos" and "delivery across
   * Lagos", which described a courier route rather than a pharmacy and capped
   * the business at one city in every search result and social unfurl. What is
   * actually being sold is pharmacist oversight and authentic medicine;
   * delivery is how it arrives, and belongs on the product and checkout pages
   * rather than in the title tag.
   */
  title: "Peaceway Online | Licensed Online Pharmacy in Nigeria",
  description:
    "A licensed Nigerian pharmacy online. Every order is reviewed by a registered pharmacist. NAFDAC-registered medicine from traceable suppliers, with clear pricing.",
  telegramBotUrl: "https://t.me/Peacewayonline_bot",
  telegramChannelUrl: "https://t.me/peacewayonline",
  instagramUrl: "https://www.instagram.com/peacewayonline?igsh=MXdiZXZ3ajM2Zng5&utm_source=qr",
  email: "peacewaypharmacy@peacewayonline.com",
  /**
   * The registered premises. Kept in full because a licensed pharmacy has to be
   * findable at a physical address - it is a compliance fact and a trust
   * signal, not a service-area claim. It belongs in the footer and on the
   * about/contact surfaces, not in a page title or a hero.
   */
  address: "Peaceway Pharmacy, Igando/Agodo Ikotun, Lagos, Nigeria",
  footerNote: "Peaceway Online is the online pharmacy service of Peaceway Pharmacy.",
  /** Named on-record so the Rx declaration and about copy cite a real role. */
  superintendentPharmacistLabel: "Superintendent Pharmacist"
} as const;

/**
 * Regulatory identity, displayed on the homepage.
 *
 * The Electronic Pharmacy Regulations 2026 require an EPSP to show, on its
 * homepage: the authorised PCN logo, the online pharmacy licence number, the
 * EPSP registration number, and a declaration that prescription-only medicines
 * are supplied only against a valid prescription from a licensed Nigerian
 * healthcare provider.
 *
 * THREE RULES FOR WHOEVER FILLS THIS IN:
 *
 * 1. Do not invent numbers. `null` renders an honest "application in progress"
 *    line. A plausible-looking placeholder number rendered as fact is a false
 *    regulatory claim, which is worse than an absent one.
 * 2. Do not set `pcnLogoApproved` until the licence is actually issued AND the
 *    PCN has authorised use of its logo. Displaying a regulator's mark before
 *    it is granted implies an approval that does not exist.
 * 3. The declaration text is not a marketing string. Change it only against the
 *    regulation's wording.
 */
export const compliance = {
  /** TODO: set to the online pharmacy licence number once PCN issues it. */
  pharmacyLicenceNumber: null as string | null,
  /** TODO: set to the EPSP registration number once issued. */
  epspRegistrationNumber: null as string | null,
  /** TODO: set to the Superintendent Pharmacist's name and PCN licence number. */
  superintendentPharmacistName: null as string | null,
  superintendentPharmacistPcnNumber: null as string | null,
  /**
   * TODO: flip to true ONLY when the licence is issued and the PCN has
   * authorised display of its logo. Until then the logo is not rendered.
   */
  pcnLogoApproved: false,
  /** Statutory declaration. Wording tracks the regulation, not the brand. */
  prescriptionDeclaration:
    "Prescription-only medicines are dispensed solely on presentation of a valid " +
    "prescription issued by a licensed healthcare provider in Nigeria. " +
    "Prescriptions are reviewed by our Superintendent Pharmacist before any " +
    "medicine is dispensed.",
  /**
   * Shown where a licence or registration has not yet been issued. This is a
   * statement about the regulator, not about us.
   */
  pendingLabel: "Application in progress",
  /**
   * Shown where the fact exists but has not been entered here yet - the
   * Superintendent Pharmacist's name and PCN number, which the pharmacy has.
   * Kept separate from `pendingLabel` on purpose: rendering "Application in
   * progress" against the pharmacist would tell a reader the premises has no
   * Superintendent, which is both false and a worse regulatory claim than the
   * blank it replaced.
   */
  notPublishedLabel: "To be published"
} as const;

/*
 * `navLinks` was removed here. It listed five anchors - #problem, #services,
 * #how-it-works, #delivery, #contact - and not one of those ids exists on the
 * landing page, which uses #s2 through #s9. Nothing imported it, so nothing was
 * broken; it was a loaded gun for whoever wired it up next.
 *
 * NOTE: `heroActions`, `sectionActions`, `sectionCopy`, `serviceCards` and
 * `deliveryAreas` below are also unreferenced - `app/page.tsx` hardcodes all of
 * it. They are left in place because, unlike navLinks, they are not wrong, and
 * deleting live-looking content config is a bigger decision than this change.
 */

export const heroActions = [
  { label: "Browse Medicines", href: "/shop", variant: "primary" as const },
  { label: "Ask a Pharmacist", href: "/ask-pharmacist", variant: "secondary" as const }
] as const;

export const sectionActions = {
  browse: { label: "Browse Medicines", href: "/shop", variant: "primary" as const },
  pharmacist: { label: "Ask a Pharmacist", href: "/ask-pharmacist", variant: "secondary" as const },
  prescription: { label: "Send a Prescription", href: "/prescription", variant: "secondary" as const },
  community: { label: "Join the Community", href: "#community", variant: "secondary" as const },
  contact: { label: "Contact the Pharmacy", href: "#contact", variant: "secondary" as const }
} as const;

export const sectionCopy = {
  hero: {
    eyebrow: "Peaceway Online · Licensed pharmacy · Nigeria",
    title: "A licensed pharmacy, online.",
    description:
      "Every order is reviewed by a registered pharmacist before it is dispensed."
  },
  problem: {
    eyebrow: "Section 02",
    title: "Most medicine is bought without a pharmacist involved.",
    description:
      "Counterfeit and substandard medicine circulates in Nigeria. Without a pharmacist, a patient has no way to tell the difference at the point of sale."
  },
  services: {
    eyebrow: "Section 03 · What We Do",
    title: "Dispensing, with a pharmacist on every order.",
    description:
      "Stock is verified, prescriptions are reviewed, and the medicine is traceable to a licensed supplier."
  },
  trust: {
    eyebrow: "Section 04 · Why Trust Us",
    title: "A registered pharmacy, not a marketplace.",
    description:
      "Peaceway Online is operated by Peaceway Pharmacy, a PCN-registered premises with a Superintendent Pharmacist on record."
  },
  howItWorks: {
    eyebrow: "Section 05 · How It Works",
    title: "Order, review, dispense.",
    description:
      "Prescription items are held until the Superintendent Pharmacist has reviewed them."
  },
  pharmacist: {
    eyebrow: "Section 06 · Ask a Pharmacist",
    title: "Speak to a pharmacist before you buy.",
    description:
      "Questions about a medicine, an interaction, or whether an item needs a prescription are answered by a registered pharmacist."
  },
  sourcing: {
    eyebrow: "Section 07 · Sourcing",
    title: "Traceable to a licensed supplier.",
    description:
      "Stock is bought through licensed distribution channels. NAFDAC registration is checked before an item is listed."
  },
  community: {
    eyebrow: "Section 08 · Community",
    title: "Medicine information from a pharmacist.",
    description:
      "Updates on stock, medicine safety notices, and answers to common questions."
  },
  contact: {
    eyebrow: "Section 09 · Contact",
    title: "Contact the pharmacy.",
    description: "Reach the pharmacy directly, or continue on Telegram."
  }
} as const;

export const serviceCards = [
  {
    title: "Pharmacist review on every order",
    text: "A registered pharmacist checks each order before it is dispensed."
  },
  {
    title: "Prescription handling",
    text: "Prescriptions are reviewed by our Superintendent Pharmacist. Prescription-only medicine is not supplied without one."
  },
  {
    title: "NAFDAC-registered medicine",
    text: "Registration is checked before an item is listed for sale."
  },
  {
    title: "Traceable sourcing",
    text: "Stock is bought through licensed distribution channels, not open markets."
  },
  {
    title: "Clear pricing",
    text: "The price you see is the price charged. Any fee is itemised before you pay."
  },
  {
    title: "Ask a pharmacist",
    text: "Questions about a medicine or an interaction are answered by a pharmacist, not a script."
  }
] as const;

/*
 * `deliveryAreas` was removed here.
 *
 * It was a hardcoded list of ten Lagos neighbourhoods rendered as a homepage
 * section, which framed the business as a courier with a coverage map. Delivery
 * is a fulfilment detail now: it appears on the product and checkout pages,
 * priced per area from the `delivery_zones` table, and nowhere else.
 *
 * The live areas were already coming from that table via `listZones()` - this
 * const was a second, drifting copy of it. See `FALLBACK_ZONES` in
 * `lib/api/customers.ts` for the offline fallback.
 */
