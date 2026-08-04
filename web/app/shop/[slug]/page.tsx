import type { Metadata } from "next";
import { permanentRedirect } from "next/navigation";
import { fetchCatalog, findProductByRef, looksLikeUuid } from "@/lib/product-slug";
import { siteConfig } from "@/lib/constants";
import { ProductDetail } from "./product-detail";

/**
 * Product page: a server component wrapping the interactive client component.
 *
 * It has to be split this way. `generateMetadata` only runs in a server
 * component, and until now this whole page was `"use client"` - so all 250
 * products served the root layout's title, `"Peaceway Online | Lagos Pharmacy"`.
 * 250 pages with one title between them is duplicate content, which is why they
 * were kept out of the sitemap. Now each one describes itself, and they can go in.
 *
 * The dynamic segment accepts a slug OR the old UUID. UUIDs were the URL format
 * until now, so they exist in bookmarks, in shared links and in Google's index;
 * they permanently redirect to the slug rather than being served in parallel, so
 * the two forms never compete for the same ranking.
 *
 * If the catalogue cannot be fetched, the page still renders: the client
 * component keeps its own fetch and takes over, exactly as it behaved before.
 * A backend hiccup degrades the metadata, not the page.
 */

type Params = { params: { slug: string } };

/** Strip markup and collapse whitespace, then cut on a word boundary. */
function summarise(text: string, limit = 155): string {
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean.length <= limit) return clean;
  const cut = clean.slice(0, limit);
  const lastSpace = cut.lastIndexOf(" ");
  return `${(lastSpace > 60 ? cut.slice(0, lastSpace) : cut).replace(/[,;:]$/, "")}…`;
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const catalog = await fetchCatalog();
  const hit = findProductByRef(params.slug, catalog);

  if (!hit) {
    return {
      title: "Medicine not found | Peaceway Online",
      robots: { index: false, follow: true },
    };
  }

  const p = hit.product;
  const name = [p.name, p.strength].filter(Boolean).join(" ");

  // The description prefers the product's own copy. Where there is none, it is
  // assembled from real attributes rather than padded with adjectives: a generic
  // marketing sentence repeated 250 times is the same duplicate-content problem
  // in a different field.
  // The fallback used to end "...with pharmacist guidance and delivery across
  // Lagos", which put a courier radius into the meta description of all 250
  // products - the single largest concentration of "we are a delivery service"
  // on the site, and the one a search result shows first. Delivery is a
  // fulfilment detail; it belongs on the page body and at checkout, not here.
  const facts = [p.dosage_form, p.category].filter(Boolean).join(", ");
  const description = p.description
    ? summarise(p.description)
    : summarise(
        `${name}${facts ? ` (${facts})` : ""} from Peaceway Pharmacy, a licensed Nigerian pharmacy. ` +
          `${p.requires_prescription ? "Prescription required. " : ""}` +
          `NAFDAC-registered medicine, dispensed after pharmacist review.`
      );

  const canonical = `/shop/${hit.slug}`;

  return {
    title: `${name} | Peaceway Online`,
    description,
    alternates: { canonical },
    openGraph: {
      title: `${name} | Peaceway Online`,
      description,
      url: canonical,
      type: "website",
      images: p.image_url
        ? [`${siteConfig.url}/api/v1${p.image_url.replace(/^\/api\/v1/, "")}`]
        : undefined,
    },
    // Out of stock is a temporary state, so the page stays indexable; it is the
    // canonical place this medicine is described either way.
    robots: { index: true, follow: true },
  };
}

export default async function ProductPage({ params }: Params) {
  const catalog = await fetchCatalog();
  const hit = findProductByRef(params.slug, catalog);

  // Send the old UUID form, and any bare slug that has since gained a collision
  // suffix, to the one canonical URL. 308 rather than 307 so the move is
  // permanent and the link equity transfers.
  if (hit && hit.slug !== decodeURIComponent(params.slug).toLowerCase()) {
    permanentRedirect(`/shop/${hit.slug}`);
  }

  return (
    <ProductDetail
      productRef={params.slug}
      initialProduct={hit?.product ?? null}
      isUuidRef={looksLikeUuid(params.slug)}
    />
  );
}
