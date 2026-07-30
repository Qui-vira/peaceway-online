import type { MetadataRoute } from "next";
import { siteConfig } from "@/lib/constants";

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
 * WHY THE 250 PRODUCT PAGES ARE NOT HERE
 *
 * They are the biggest SEO opportunity in this app and they are not ready.
 * `/shop/[id]` is a client component with no `generateMetadata`, so all 250
 * products currently serve the same <title> as the homepage. Listing them would
 * submit 250 duplicate-title pages, which suppresses a site rather than
 * promoting it. Two things have to land first:
 *
 *   1. per-product `generateMetadata` (title, description, OG image)
 *   2. ideally slugs instead of UUIDs - `/shop/paracetamol-500mg` carries the
 *      search term, `/shop/4094c822-8450-...` carries nothing
 *
 * Once those exist, add them here by fetching `/catalog` inside a try/catch that
 * degrades to these static routes, so a backend hiccup can never fail the build.
 *
 * `lastModified` is intentionally omitted. Stamping every entry with the build
 * time would tell Google the whole site changed on every deploy, which is not
 * true and which teaches it to distrust the signal.
 */
export default function sitemap(): MetadataRoute.Sitemap {
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

  return routes.map(({ path, priority, changeFrequency }) => ({
    url: `${base}${path}`,
    priority,
    changeFrequency,
  }));
}
