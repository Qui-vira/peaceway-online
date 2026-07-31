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
 * A hook, not a component in the JSX. The first version of this was
 * `<PageTitle title="..." />` placed next to the `<h1>` it mirrored, which read
 * nicely and was wrong: these pages return early for loading, guest, error and
 * empty states - `/start` has eight returns, `/request` seven - so the title was
 * only set on whichever branch happened to contain the element. A signed-out
 * visitor to `/prescription` saw the homepage's title, because the tag sat in
 * the success branch. A hook called at the top of the component runs on every
 * render path by construction, which is the property this actually needs.
 */
export function usePageTitle(title: string): void {
  useEffect(() => {
    const previous = document.title;
    document.title = `${title} · Peaceway Online`;
    // Restore on unmount so a route that does not set its own title does not
    // inherit the last one that did.
    return () => {
      document.title = previous;
    };
  }, [title]);
}
