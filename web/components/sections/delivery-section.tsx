import { deliveryAreas, sectionCopy } from "@/lib/constants";
import { media } from "@/lib/media";
import { SectionShell } from "@/components/ui/section-shell";

export function DeliverySection(): JSX.Element {
  return (
    <SectionShell
      id="delivery"
      eyebrow={sectionCopy.delivery.eyebrow}
      title={sectionCopy.delivery.title}
      description={sectionCopy.delivery.description}
      videoSrc={media.deliveryVideo}
      poster={media.sectionPoster}
    >
      <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-start">
        <div className="flex flex-wrap gap-3">
          {deliveryAreas.map((area, index) => (
            <span
              key={area}
              className={
                index < 3
                  ? "inline-flex min-h-10 items-center rounded-full border border-emerald-500/35 bg-emerald-500/12 px-4 text-sm font-semibold text-t"
                  : "inline-flex min-h-10 items-center rounded-full border border-white/10 bg-white/5 px-4 text-sm text-m"
              }
            >
              {area}
            </span>
          ))}
        </div>

        <div className="glass rounded-[1.4rem] p-6">
          <svg viewBox="0 0 320 280" className="block w-full" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path
              d="M28 250 Q48 222 76 205 Q106 187 144 177 Q178 170 210 175 Q242 180 270 163 Q292 149 302 127 Q297 90 278 64 Q256 36 222 28 Q188 20 156 32 Q124 44 100 66 Q76 88 58 114 Q40 138 32 168 Z"
              fill="rgba(15,103,60,0.06)"
              stroke="rgba(15,103,60,0.18)"
              strokeWidth="1.5"
            />
            <circle cx="138" cy="195" r="16" fill="rgba(15,103,60,0.2)" stroke="#0F673C" strokeWidth="1.5" />
            <circle cx="138" cy="195" r="5" fill="#0F673C" />
            <text x="156" y="200" fontSize="11" fill="#0F673C" fontFamily="DM Sans,sans-serif" fontWeight="700">
              Igando
            </text>
            <circle cx="162" cy="172" r="5" fill="rgba(15,103,60,0.45)" stroke="#0F673C" strokeWidth="1" />
            <text x="170" y="176" fontSize="9" fill="rgba(177,189,176,0.65)" fontFamily="DM Sans,sans-serif">
              Agodo
            </text>
            <circle cx="108" cy="215" r="5" fill="rgba(15,103,60,0.4)" stroke="rgba(15,103,60,0.6)" strokeWidth="1" />
            <text x="116" y="219" fontSize="9" fill="rgba(177,189,176,0.65)" fontFamily="DM Sans,sans-serif">
              Ikotun
            </text>
          </svg>
        </div>
      </div>
    </SectionShell>
  );
}
