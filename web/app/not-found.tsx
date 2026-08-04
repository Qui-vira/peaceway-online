import type { Metadata } from "next";
import Link from "next/link";

/**
 * 404.
 *
 * The site had no `not-found.tsx`, so a mistyped URL fell through to Next's
 * default black-on-white "This page could not be found" - a page with no
 * wordmark, no way back, and nothing identifying it as belonging to a pharmacy.
 * A customer who lands there has no reason to believe the rest of the site is
 * real.
 *
 * Server component with static metadata, so a crawler that reaches a dead link
 * gets a `noindex` and a route back into the catalogue rather than a blank.
 */
export const metadata: Metadata = {
  title: "Page not found | Peaceway Online",
  robots: { index: false, follow: true }
};

export default function NotFound(): JSX.Element {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-[#0b0c09] px-5 py-16 text-center">
      <p className="text-2xs font-semibold uppercase tracking-[0.18em] text-emerald-400">
        Peaceway Online
      </p>
      <h1 className="mt-3 font-syne text-xl font-bold text-white">
        This page does not exist.
      </h1>
      <p className="mt-2 max-w-sm text-xs-plus leading-relaxed text-[#b1bdb0]">
        The link may be out of date, or the medicine may no longer be listed.
      </p>

      <div className="mt-8 flex flex-col gap-3">
        <Link href="/shop" className="pw-btn">
          Browse medicines
        </Link>
        <Link
          href="/ask-pharmacist"
          className="inline-flex min-h-[44px] items-center justify-center rounded-2xl px-5 text-xs-plus font-semibold text-[#b1bdb0] transition hover:text-white focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[rgba(52,217,138,0.5)]"
        >
          Ask a pharmacist
        </Link>
      </div>
    </main>
  );
}
