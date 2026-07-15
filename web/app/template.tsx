import type { ReactNode } from "react";

/**
 * Route transition.
 *
 * `template.tsx` (not `layout.tsx`) is the right file: Next remounts a template
 * on every navigation, which is exactly the lifecycle an entrance needs. A
 * layout persists and would animate once, ever.
 *
 * Deliberately small: 180ms, opacity plus a 6px rise. Every navigation in the
 * product passes through here, so this is the most-seen motion in the app and
 * the one with the least licence to be interesting. It exists to say "this
 * screen came from that one" - without it every navigation is a hard cut.
 *
 * CSS, not framer-motion, and not by preference. framer applies `initial` as an
 * inline style that Next renders into the SSR HTML: the server was shipping
 * `<div style="opacity:0">` around every route, so any failure to hydrate -
 * bundle error, blocked JS, a slow phone - left the whole page permanently
 * blank. A route-level wrapper must not be able to fail closed. The CSS
 * animation's base state is visible, needs no JS, and rides the compositor.
 *
 * No exit animation: AnimatePresence on a route boundary means holding the old
 * screen while the new one loads, which delays the thing the user asked for.
 * Enter-only keeps navigation instant and still buys the continuity.
 *
 * This is also a server component now - no "use client", no framer on the
 * critical path of every route.
 */
export default function Template({ children }: { children: ReactNode }) {
  return <div className="pw-route">{children}</div>;
}
