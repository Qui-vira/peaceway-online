import { sectionCopy } from "@/lib/constants";
import { media } from "@/lib/media";
import { SectionShell } from "@/components/ui/section-shell";

const steps = [
  "Click Order on Telegram",
  "Tell the bot what you need",
  "Confirm product and quantity",
  "Enter your delivery area",
  "Confirm total and delivery fee",
  "Pay for your order",
  "Peaceway packages your order",
  "Logistics partner delivers",
  "You track the order",
  "Peaceway follows up"
] as const;

export function HowItWorksSection(): JSX.Element {
  return (
    <SectionShell
      id="how-it-works"
      eyebrow={sectionCopy.howItWorks.eyebrow}
      title={sectionCopy.howItWorks.title}
      description={sectionCopy.howItWorks.description}
      videoSrc={media.howItWorksVideo}
      poster={media.sectionPoster}
    >
      <div className="grid gap-4 md:grid-cols-2">
        {steps.map((step, index) => (
          <div
            key={step}
            className="glass rounded-2xl p-5 transition-all duration-500 ease-out"
            style={{
              transitionDelay: `${index * 45}ms`
            }}
          >
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full border border-emerald-500/35 bg-emerald-500/10 font-display text-sm font-extrabold text-g">
              {index + 1}
            </div>
            <h3 className="section-title mb-1 text-base font-bold text-t">{step}</h3>
            <p className="text-sm leading-6 text-m">
              {index < 5
                ? "Simple customer flow, designed for Telegram."
                : "A clean handoff from confirmation through delivery and follow-up."}
            </p>
          </div>
        ))}
      </div>
    </SectionShell>
  );
}
