"use client";

/**
 * Referral attribution, client side.
 *
 * The share link used to point at `peaceway.online` - a domain the pharmacy
 * does not own - and nothing anywhere read the `?ref=` parameter, so a referral
 * link landed on the marketing homepage and the code evaporated. The link now
 * uses `siteConfig.url`, and this module is the other half: capture the code on
 * arrival, hold it until the person actually signs up, and send it with the
 * registration.
 *
 * `localStorage`, not a cookie or a URL round-trip, because the gap between
 * clicking a friend's link and finishing sign-up is usually several minutes and
 * at least one page.
 */

const KEY = "pw_referral";

/**
 * Codes are minted server-side as `PW` + up to 3 initials + 4 chars from an
 * unambiguous alphabet. Validate loosely but do validate: this value goes
 * straight into a request body from a URL a stranger controls.
 */
const CODE_RE = /^PW[A-Z0-9]{2,14}$/;

export function captureReferral(search: string): void {
  if (typeof window === "undefined") return;
  try {
    const raw = new URLSearchParams(search).get("ref");
    if (!raw) return;
    const code = raw.trim().toUpperCase();
    if (!CODE_RE.test(code)) return;
    // First link wins. Someone who arrives via one friend and later clicks
    // another's should stay attributed to whoever actually convinced them.
    if (window.localStorage.getItem(KEY)) return;
    window.localStorage.setItem(KEY, code);
  } catch {
    // Private mode, storage disabled, malformed query - none of which should
    // stop the page rendering.
  }
}

export function readReferral(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function clearReferral(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    /* nothing to clean up */
  }
}
