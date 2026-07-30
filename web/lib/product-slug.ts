import type { Product } from "@/lib/api/catalog";

/**
 * Product URL slugs, derived rather than stored.
 *
 * There is no `slug` column on `Product`. Adding one means an Alembic migration
 * and a backfill against the production database, so instead the slug is
 * computed from fields that already exist and resolved by matching against the
 * catalogue. The catalogue is 250 items in a single ~90KB response, which is
 * small enough to fetch and scan per render, and it is cached (see
 * `fetchCatalogCached`).
 *
 * Why this matters at all: the old URLs were `/shop/4094c822-8450-4cfc-b330-
 * f46a304d95d3`. A UUID carries no search term. `/shop/paracetamol-500mg` names
 * the thing a person actually typed into Google, in the URL, which is one of the
 * few remaining places a keyword still counts for something.
 */

/** Strip to a-z0-9 and single hyphens. Diacritics are folded, not dropped. */
function kebab(input: string): string {
  return input
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

/**
 * The slug for a product, before collision handling.
 *
 * Name plus strength, because "Paracetamol" alone is ambiguous across a
 * pharmacy's shelf: 500mg tablets and 120mg/5ml suspension are different
 * products a customer must not confuse. Strength is the field that
 * distinguishes them and it is also what people search.
 */
export function baseProductSlug(p: Pick<Product, "name" | "strength">): string {
  const parts = [p.name, p.strength ?? ""].filter(Boolean).join(" ");
  return kebab(parts) || "product";
}

/**
 * The slug used in URLs. Always carries an 8-character id suffix.
 *
 * The suffix is unconditional, and that is a deliberate trade of a little
 * tidiness for correctness. Suffixing only on collision requires knowing the
 * whole catalogue to build a link, and the pages that render product links hold
 * a *filtered* list - so a colliding product would be linked with a bare slug
 * that cannot be resolved unambiguously, and 404. Unconditional means any
 * caller can build a correct link from the product alone.
 *
 * It costs nothing that matters. Search engines read `paracetamol-500mg` in
 * `/shop/paracetamol-500mg-4094c822` exactly the same way; the keywords are
 * still in the path, which was the entire point of moving off bare UUIDs.
 */
export function productSlug(product: Pick<Product, "id" | "name" | "strength">): string {
  return `${baseProductSlug(product)}-${product.id.slice(0, 8)}`;
}

/** True when the path segment is a UUID rather than a slug. */
export function looksLikeUuid(ref: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(ref);
}

/**
 * Find a product from a URL segment, accepting either form.
 *
 * UUIDs are still accepted because they were the URL format until now: existing
 * links, anything a customer bookmarked, and anything already in Google's index
 * all use them. The page redirects those to the slug rather than serving both,
 * so the two forms never compete as duplicate content.
 */
export function findProductByRef(
  ref: string,
  catalog: Product[]
): { product: Product; slug: string } | null {
  const decoded = decodeURIComponent(ref).toLowerCase();

  if (looksLikeUuid(decoded)) {
    const byId = catalog.find((p) => p.id.toLowerCase() === decoded);
    return byId ? { product: byId, slug: productSlug(byId) } : null;
  }

  // The last hyphenated group is the 8-character id prefix. Matching on that
  // rather than the whole slug means a product renamed or re-priced still
  // resolves from an old link, and then redirects to its current slug.
  const shortId = decoded.split("-").pop() ?? "";
  if (/^[0-9a-f]{8}$/.test(shortId)) {
    const byShortId = catalog.find((p) => p.id.toLowerCase().startsWith(shortId));
    if (byShortId) return { product: byShortId, slug: productSlug(byShortId) };
  }

  const exact = catalog.find((p) => productSlug(p) === decoded);
  if (exact) return { product: exact, slug: productSlug(exact) };

  // A legacy bare slug with no suffix, from before this scheme.
  const byBase = catalog.filter((p) => baseProductSlug(p) === decoded);
  if (byBase.length === 1) return { product: byBase[0], slug: productSlug(byBase[0]) };

  return null;
}

/**
 * The catalogue, fetched server-side.
 *
 * Uses INTERNAL_API_URL, not the client's route. `getApiBase()` returns the
 * relative `/api/v1` proxy path in the browser, which a server component cannot
 * fetch, and its server branch reads NEXT_PUBLIC_API_URL. INTERNAL_API_URL is
 * the server-only variable that already points at Railway for the rewrite in
 * next.config.mjs, so it is the one guaranteed to be correct here.
 *
 * Cached for an hour. A stale price on a page Google is crawling is a far
 * smaller problem than 250 uncached catalogue fetches, and the interactive
 * client component fetches live data for the parts a customer acts on.
 */
export async function fetchCatalog(): Promise<Product[]> {
  const internal = process.env.INTERNAL_API_URL;
  if (!internal) return [];

  const base = internal.replace(/\/$/, "");
  const apiBase = base.endsWith("/api/v1") ? base : `${base}/api/v1`;

  try {
    const res = await fetch(`${apiBase}/catalog`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    const data: unknown = await res.json();
    return Array.isArray(data) ? (data as Product[]) : [];
  } catch {
    // Never let a backend hiccup fail a page render or a build. Callers treat an
    // empty catalogue as "cannot resolve", which falls through to the client
    // component's own fetch.
    return [];
  }
}
