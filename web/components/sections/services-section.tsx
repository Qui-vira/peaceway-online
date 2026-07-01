import { sectionCopy, serviceCards } from "@/lib/constants";
import { media } from "@/lib/media";
import { SectionShell } from "@/components/ui/section-shell";
import { GlassCard } from "@/components/ui/glass-card";

export function ServicesSection(): JSX.Element {
  return (
    <SectionShell
      id="services"
      eyebrow={sectionCopy.services.eyebrow}
      title={sectionCopy.services.title}
      description={sectionCopy.services.description}
      videoSrc={media.servicesVideo}
      poster={media.sectionPoster}
    >
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {serviceCards.map((card, index) => (
          <GlassCard
            key={card.title}
            variant="green"
            title={card.title}
            text={card.text}
            delay={index * 0.06}
          />
        ))}
      </div>
    </SectionShell>
  );
}
