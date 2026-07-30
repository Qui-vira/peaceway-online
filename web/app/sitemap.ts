import type { MetadataRoute } from "next";
import { siteConfig } from "@/lib/constants";
import { fetchCatalog, productSlug } from "@/lib/product-slug";

/**
 * The sitemap, generated from the routes rather than hand-maintained.
 *
 * Replaces a static `public/sitemap.xml` that listed exactly one URL - the
 * homepage - and listed it on `peacewayonline.com.ng`, a domain with no DNS. So
 * Google could not fetch the sitemap, and if it had, it would have learned about
 * one page. Origin now comes from `siteConfig.url`, the same value `metadataBase`
 * uses, so the two cannot drift apart again.
 *
 * `public/sitemap.xml` had to be deleted for this to work: a static file in
 * `public/` is served directly and shadows the generated route of the same name.
 *
 * WHAT BELONGS HERE
 *
 * A sitemap is a list of pages a stranger should be able to find in search, not
 * an inventory of routes. Every route in this app returns 200 to an anonymous
 * request - they are client-rendered shells, and the guest wall only appears
 * after hydration - so "does it return 200" cannot be the test. The test is
 * whether the page has stable, meaningful content for someone who has never
 * logged in.
 *
 * Excluded, deliberately:
 *   /app /cart /profile /referral /orders* /reminders* /requests*
 *       Personal surfaces. Nothing for a stranger to rank on, and indexing them
 *       spends crawl budget on near-identical thin pages.
 *   /admin/* /dispatch
 *       Staff only.
 *   /offline
 *       The PWA fallback shell. Indexing it would put an error page in results.
 *   /showcase
 *       Internal.
 *
 * THE PRODUCT PAGES
 *
 * Included now that they earn it. They were held back while `/shop/[id]` was a
 * client component with no `generateMetadata`, which made all 250 serve the
 * homepage's <title> - submitting 250 duplicate-title pages suppresses a site
 * rather than promoting it. Each product now describes itself and sits on a
 * keyword-bearing slug, so they belong here. For a pharmacy this is where the
 * search traffic actually is: people search medicine names, not "pharmacy".
 *
 * The catalogue fetch cannot fail the build. `fetchCatalog` swallows its own
 * errors and returns an empty array, so a backend hiccup degrades this to the
 * static routes below rather than breaking the deploy.
 *
 * `lastModified` is intentionally omitted. Stamping every entry with the build
 * time would tell Google the whole site changed on every deploy, which is not
 * true and which teaches it to distrust the signal.
 */
/**
 * Rebuilt hourly rather than pinned at deploy time, so a medicine added to the
 * catalogue appears in the sitemap without anyone shipping code - and so a
 * catalogue that was unreachable during a build is not baked into a
 * products-less sitemap until the next deploy.
 */
export const revalidate = 3600;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = siteConfig.url;

  const routes: Array<{
    path: string;
    priority: number;
    changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"];
  }> = [
    // The marketing home: what the brand ranks on.
    { path: "/", priority: 1.0, changeFrequency: "weekly" },
    // The catalogue. Highest-intent public page after the homepage, and its
    // contents move as stock does.
    { path: "/shop", priority: 0.9, changeFrequency: "daily" },
    // A pharmacist answering questions is the service, not a feature.
    { path: "/ask-pharmacist", priority: 0.8, changeFrequency: "monthly" },
    // Both are real entry points for someone arriving with a specific need.
    { path: "/prescription", priority: 0.7, changeFrequency: "monthly" },
    { path: "/request", priority: 0.7, changeFrequency: "monthly" },
    // Onboarding. Worth indexing as a landing target, below the service pages.
    { path: "/start", priority: 0.6, changeFrequency: "monthly" },
    // Utility, but public and something people search for by name.
    { path: "/track", priority: 0.5, changeFrequency: "monthly" },
    // Wholesalers and suppliers, a different and much smaller audience.
    { path: "/partners", priority: 0.4, changeFrequency: "monthly" },
  ];

  const staticEntries: MetadataRoute.Sitemap = routes.map(
    ({ path, priority, changeFrequency }) => ({
      url: `${base}${path}`,
      priority,
      changeFrequency,
    })
  );

  // Priority 0.6: below the service pages that describe what the pharmacy does,
  // above /partners. Weekly, because what moves on a product page is price and
  // stock rather than the medicine itself.
  const productEntries: MetadataRoute.Sitemap = (await fetchCatalog()).map((p) => ({
    url: `${base}/shop/${productSlug(p)}`,
    priority: 0.6,
    changeFrequency: "weekly" as const,
  }));

  return [...staticEntries, ...productEntries];
}
