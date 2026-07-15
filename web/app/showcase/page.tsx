import { ParallaxShowcase } from "@/components/ui/parallax-showcase";
import { StickyWalkthrough } from "@/components/ui/sticky-walkthrough";

/**
 * Preview page for the new GSAP scroll sections (parallax depth + sticky
 * walkthrough). Kept off the main carousel landing so they can be reviewed in a
 * normal vertical-scroll context; drop the components into page.tsx once the
 * placement is decided.
 */
export default function ShowcasePage(): JSX.Element {
  return (
    <main className="min-h-screen bg-[#0b0c09]">
      <ParallaxShowcase />
      <StickyWalkthrough />
      <div className="h-[30vh]" />
    </main>
  );
}
