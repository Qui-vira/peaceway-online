import { sectionCopy } from "@/lib/constants";
import { media } from "@/lib/media";
import { SectionShell } from "@/components/ui/section-shell";
import { GlassCard } from "@/components/ui/glass-card";

export function ProblemSection(): JSX.Element {
  return (
    <SectionShell
      id="problem"
      eyebrow={sectionCopy.problem.eyebrow}
      title={sectionCopy.problem.title}
      description={sectionCopy.problem.description}
      videoSrc={media.problemVideo}
      poster={media.sectionPoster}
    >
      <div className="grid gap-5 md:grid-cols-3">
        <GlassCard
          variant="red"
          title="Wrong advice from unqualified sources"
          text="Unqualified sellers can create avoidable risk when people need simple, reliable guidance."
          delay={0.05}
        />
        <GlassCard
          variant="red"
          title="Counterfeit and substandard medicines"
          text="A real pharmacy workflow helps keep the buying experience tied to proper sourcing."
          delay={0.12}
        />
        <GlassCard
          variant="red"
          title="Unnecessary movement across Lagos"
          text="Medicine should not require extra travel when a pharmacy can support you digitally."
          delay={0.19}
        />
      </div>
    </SectionShell>
  );
}
