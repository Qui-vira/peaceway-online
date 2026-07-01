import Image from "next/image";
import { sectionCopy } from "@/lib/constants";
import { media } from "@/lib/media";
import { SectionShell } from "@/components/ui/section-shell";

const trustItems = [
  ["Physical pharmacy in Igando/Agodo Ikotun", "A real location, real staff, and a real service model."],
  ["Pharmacist-led service", "Orders and questions remain within a pharmacy-led workflow."],
  ["Genuine, properly sourced medicines", "The digital front end supports a real pharmacy operation."],
  ["Prescription review where required", "Higher-risk items can be reviewed before supply."]
] as const;

export function TrustSection(): JSX.Element {
  return (
    <SectionShell
      id="trust"
      eyebrow={sectionCopy.trust.eyebrow}
      title={sectionCopy.trust.title}
      description={sectionCopy.trust.description}
      videoSrc={media.trustVideo}
      poster={media.trustPoster}
    >
      <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
        <div className="overflow-hidden rounded-[1.5rem] border border-white/10 bg-white/5 shadow-glow">
          <Image
            src={media.pharmacyPhoto}
            alt="Peaceway Pharmacy"
            width={1400}
            height={900}
            className="h-full w-full object-cover"
          />
        </div>

        <div className="space-y-4">
          {trustItems.map(([title, text]) => (
            <div key={title} className="border-b border-white/6 pb-4 last:border-b-0">
              <h3 className="section-title mb-1 text-lg font-bold text-t">{title}</h3>
              <p className="text-sm leading-6 text-m">{text}</p>
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}
