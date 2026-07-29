import type { ReactNode } from "react";

/**
 * Route transition.
 *
 * `template.tsx` (not `layout.tsx`) is the right file: Next remounts a template
 * on every navigation, which is exactly the lifecycle an entrance needs. A
 * layout persists and would animate once, ever.
 *
 * All this does is the 180ms opacity-and-6px-rise defined by `.pw-route`, and
 * that restraint is the whole point.
 *
 * A full-screen branded curtain used to sweep over the viewport here on every
 * navigation. It was removed on purpose. The first question to ask of any
 * animation is how often the user will see it, and a route transition in a
 * pharmacy app fires dozens of times per session: browse, open a product, back,
 * open another, cart, checkout. At that frequency an animation stops reading as
 * craft and starts reading as latency, and the user is left waiting on a logo
 * they have already seen. Animations seen that often should be removed or made
 * nearly invisible, not made more elaborate. The brand moment belongs on app
 * open, where it happens once.
 *
 * CSS, not framer-motion, and not by preference. framer applies `initial` as an
 * inline style that Next renders into the SSR HTML: the server was shipping
 * `<div style="opacity:0">` around every route, so any failure to hydrate -
 * bundle error, blocked JS, a slow phone - left the whole page permanently
 * blank. A route-level wrapper must not be able to fail closed. The CSS
 * animation's base state is visible, needs no JS, and rides the compositor.
 */
export default function Template({ children }: { children: ReactNode }) {
  return <div className="pw-route">{children}</div>;
}
