"use client";

import { useEffect } from "react";

/**
 * Sets `document.title` for a client-rendered route.
 *
 * Every screen in the app shipped the marketing homepage's title - "Peaceway
 * Online | Lagos Pharmacy - Order Medicine on Telegram" - because these are all
 * `"use client"` pages and `export const metadata` is a server-component API.
 * With six tabs open on a phone, cart, order and shop were indistinguishable.
 *
 * A component rather than a hook so it can sit in the JSX next to the `<h1>` it
 * mirrors, which is the thing most likely to be edited alongside it.
 */
export function PageTitle({ title }: { title: string }) {
  useEffect(() => {
    const previous = document.title;
    document.title = `${title} · Peaceway Online`;
    // Restore on unmount so a route that does not set its own title does not
    // inherit the last one that did.
    return () => {
      document.title = previous;
    };
  }, [title]);
  return null;
}
