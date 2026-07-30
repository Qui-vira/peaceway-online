"use client";

import { useEffect } from "react";
import { captureReferral } from "@/lib/referral";

/**
 * Records a `?ref=` code on arrival, anywhere on the site.
 *
 * Mounted at the layout root rather than on the landing page, because a
 * referral link is shared as a bare URL and people paste it with paths
 * attached - straight to a product, to /shop, to /prescription. Attribution
 * should not depend on which page the link happened to point at.
 *
 * Reads `window.location.search` directly instead of `useSearchParams`: that
 * hook opts the whole subtree into client-side rendering with a Suspense
 * requirement, which is a heavy price for a side effect that renders nothing.
 */
export function ReferralCapture(): null {
  useEffect(() => {
    captureReferral(window.location.search);
  }, []);
  return null;
}
