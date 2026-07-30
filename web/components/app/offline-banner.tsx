"use client";

import { useEffect, useState } from "react";
import { WifiOff } from "lucide-react";

/**
 * Tells the customer when the phone, not the pharmacy, is the problem.
 *
 * There is a service worker and an `/offline` fallback page, but those only
 * cover a *navigation* made while offline. A connection dropped while the app
 * is already open surfaced as "we couldn't reach the pharmacy" on whichever
 * screen happened to be fetching - which reads as "this pharmacy is broken"
 * rather than "your data cut out", and on Lagos mobile data the second is far
 * more likely.
 *
 * Deliberately a banner and not a blocking overlay: everything already loaded
 * stays usable, and the cart lives in localStorage, so an offline customer can
 * keep browsing what they have.
 */
export function OfflineBanner() {
  // `null` until mounted: `navigator.onLine` does not exist on the server, and
  // assuming "online" would flash the banner away on a genuinely offline load.
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  if (online !== false) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="sticky top-0 z-[45] flex items-center justify-center gap-2 border-b border-amber-500/25 bg-amber-500/12 px-4 py-2 text-[13px] text-amber-200"
    >
      <WifiOff className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      You&apos;re offline. We&apos;ll reconnect automatically.
    </div>
  );
}
