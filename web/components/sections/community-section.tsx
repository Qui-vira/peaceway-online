import { sectionCopy } from "@/lib/constants";
import { media } from "@/lib/media";
import { SectionShell } from "@/components/ui/section-shell";

export function CommunitySection(): JSX.Element {
  return (
    <SectionShell
      id="community"
      eyebrow={sectionCopy.community.eyebrow}
      title={sectionCopy.community.title}
      description={sectionCopy.community.description}
      videoSrc={media.communityVideo}
      poster={media.sectionPoster}
      align="center"
      compact
    >
      <div className="mx-auto grid max-w-4xl gap-4 md:grid-cols-2">
        <a
          href="https://t.me/peacewayonline"
          target="_blank"
          rel="noreferrer noopener"
          className="glass rounded-[1.4rem] p-6 text-left transition hover:-translate-y-1 hover:bg-white/10"
        >
          <p className="section-title mb-2 text-lg font-bold text-t">Join Telegram Channel</p>
          <p className="text-sm leading-6 text-m">Health updates, product alerts, and pharmacy news in one place.</p>
        </a>
        <a
          href="https://t.me/Peacewayonline_bot"
          target="_blank"
          rel="noreferrer noopener"
          className="glass rounded-[1.4rem] border-emerald-500/25 bg-emerald-500/10 p-6 text-left transition hover:-translate-y-1 hover:bg-emerald-500/15"
        >
          <p className="section-title mb-2 text-lg font-bold text-t">Order on Telegram Bot</p>
          <p className="text-sm leading-6 text-m">Browse, ask, order, and track in the same Telegram flow.</p>
        </a>
      </div>
    </SectionShell>
  );
}
