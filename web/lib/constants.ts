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
  title: "Peaceway Online | Lagos Pharmacy - Order Medicine on Telegram",
  description:
    "Genuine medicines, pharmacist guidance, and delivery across Lagos. Order through Telegram from Peaceway Pharmacy, Igando.",
  telegramBotUrl: "https://t.me/Peacewayonline_bot",
  telegramChannelUrl: "https://t.me/peacewayonline",
  instagramUrl: "https://www.instagram.com/peacewayonline?igsh=MXdiZXZ3ajM2Zng5&utm_source=qr",
  email: "peacewaypharmacy@peacewayonline.com",
  address: "Peaceway Pharmacy, Igando/Agodo Ikotun, Lagos",
  footerNote: "Peaceway Online is an online service of Peaceway Pharmacy."
} as const;

export const navLinks = [
  { label: "About", href: "#problem" },
  { label: "Services", href: "#services" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "Delivery", href: "#delivery" },
  { label: "Contact", href: "#contact" }
] as const;

export const heroActions = [
  { label: "Order on Telegram", href: siteConfig.telegramBotUrl, variant: "primary" as const },
  { label: "Join Our Community", href: siteConfig.telegramChannelUrl, variant: "secondary" as const }
] as const;

export const sectionActions = {
  order: { label: "Order on Telegram", href: siteConfig.telegramBotUrl, variant: "primary" as const },
  pharmacist: { label: "Ask a Pharmacist", href: "#pharmacist", variant: "secondary" as const },
  community: { label: "Join the Community", href: "#community", variant: "secondary" as const },
  delivery: { label: "View Delivery Areas", href: "#delivery", variant: "secondary" as const },
  contact: { label: "Contact Peaceway", href: "#contact", variant: "secondary" as const }
} as const;

export const sectionCopy = {
  hero: {
    eyebrow: "Peaceway Online · Igando, Lagos, Nigeria",
    title: "Your Lagos pharmacy is now online.",
    description: "Genuine medicines, pharmacist guidance, and delivery across Lagos."
  },
  problem: {
    eyebrow: "Section 02",
    title: "Buying medicine should not feel like guessing.",
    description:
      "In Lagos, getting the right medicine can feel risky. Wrong advice, counterfeit products, and unnecessary movement should not be part of healthcare."
  },
  services: {
    eyebrow: "Section 03 · What We Do",
    title: "Order medicine. Ask a pharmacist. Get it delivered.",
    description: "A simple Telegram-first experience built around pharmacy service."
  },
  trust: {
    eyebrow: "Section 04 · Why Trust Us",
    title: "A real pharmacy behind the online service.",
    description:
      "Peaceway Online extends an existing pharmacy service into a clean, digital ordering experience."
  },
  howItWorks: {
    eyebrow: "Section 05 · How It Works",
    title: "From message to delivery.",
    description: "Ten simple steps. Telegram first, no heavy app install required."
  },
  pharmacist: {
    eyebrow: "Section 06 · Ask a Pharmacist",
    title: "Need help before you buy?",
    description:
      "Use Telegram to ask questions about medicine choices, availability, or whether a product needs pharmacist review."
  },
  delivery: {
    eyebrow: "Section 07 · Delivery Areas",
    title: "Delivery across Lagos, starting from Igando.",
    description:
      "We focus on nearby Lagos communities first and can expand coverage as operations grow."
  },
  community: {
    eyebrow: "Section 08 · Community",
    title: "Join the Peaceway health community.",
    description: "Stay informed, get updates, and ask questions in a simple Telegram-native flow."
  },
  contact: {
    eyebrow: "Section 09 · Contact",
    title: "Talk to Peaceway.",
    description: "Use the channels below to reach the pharmacy or continue on Telegram."
  }
} as const;

export const serviceCards = [
  {
    title: "OTC Medicine Delivery",
    text: "Order over-the-counter medicines directly through Telegram."
  },
  {
    title: "Pharmacist Questions via Telegram",
    text: "Ask a pharmacist before ordering if you want guidance."
  },
  {
    title: "Product Availability Check",
    text: "We verify stock before confirming an order."
  },
  {
    title: "Prescription Review",
    text: "Prescription products can be reviewed before supply."
  },
  {
    title: "Delivery Across Selected Lagos Areas",
    text: "Start with Igando and nearby Lagos communities."
  },
  {
    title: "Customer Support and Follow-up",
    text: "A simple customer experience with post-delivery follow-up."
  }
] as const;

export const deliveryAreas = [
  "Igando",
  "Agodo",
  "Ikotun",
  "Egbeda",
  "Isheri",
  "Idimu",
  "Iyana Ipaja",
  "Egbe",
  "Ejigbo",
  "Ijegun"
] as const;
