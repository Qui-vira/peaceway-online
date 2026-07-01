import { sectionCopy } from "@/lib/constants";
import { media } from "@/lib/media";
import { SectionShell } from "@/components/ui/section-shell";

export function PharmacistSection(): JSX.Element {
  return (
    <SectionShell
      id="pharmacist"
      eyebrow={sectionCopy.pharmacist.eyebrow}
      title={sectionCopy.pharmacist.title}
      description={sectionCopy.pharmacist.description}
      videoSrc={media.pharmacistVideo}
      poster={media.sectionPoster}
    >
      <div className="mx-auto grid max-w-4xl gap-4 lg:grid-cols-2">
        <div className="glass rounded-[1.4rem] rounded-br-sm p-5 text-left">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-white/55">Customer</p>
          <p className="text-sm leading-7 text-t">Can I ask about a medicine before I order?</p>
        </div>
        <div className="glass rounded-[1.4rem] rounded-bl-sm border-emerald-500/25 bg-emerald-500/10 p-5 text-left">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-200">Peaceway Pharmacist</p>
          <p className="text-sm leading-7 text-m">
            Yes. Send the product name and the question you want answered, and we will guide you through the right next step.
          </p>
        </div>
        <div className="glass rounded-[1.4rem] rounded-br-sm p-5 text-left">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-white/55">Customer</p>
          <p className="text-sm leading-7 text-t">What if the item needs review?</p>
        </div>
        <div className="glass rounded-[1.4rem] rounded-bl-sm border-emerald-500/25 bg-emerald-500/10 p-5 text-left">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-200">Peaceway Pharmacist</p>
          <p className="text-sm leading-7 text-m">
            Some products need pharmacist review before supply. That workflow remains in the Telegram bot.
          </p>
        </div>
      </div>
    </SectionShell>
  );
}
