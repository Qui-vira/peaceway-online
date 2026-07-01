import Image from "next/image";
import { sectionCopy, siteConfig } from "@/lib/constants";
import { media } from "@/lib/media";
import { SectionShell } from "@/components/ui/section-shell";

const contacts = [
  ["Email", siteConfig.email, `mailto:${siteConfig.email}`],
  ["Telegram Bot", "t.me/Peacewayonline_bot", "https://t.me/Peacewayonline_bot"],
  ["Telegram Channel", "t.me/peacewayonline", "https://t.me/peacewayonline"],
  ["Address", siteConfig.address, "#contact"],
  ["Instagram", "@peacewayonline", siteConfig.instagramUrl]
] as const;

export function ContactSection(): JSX.Element {
  return (
    <SectionShell
      id="contact"
      eyebrow={sectionCopy.contact.eyebrow}
      title={sectionCopy.contact.title}
      description={sectionCopy.contact.description}
      videoSrc={media.contactVideo}
      poster={media.sectionPoster}
      compact
    >
      <div className="grid gap-6 lg:grid-cols-[0.98fr_1.02fr] lg:items-start">
        <div className="space-y-5">
          <div className="overflow-hidden rounded-[1.6rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.12),rgba(255,255,255,0.05))] p-4 shadow-[0_24px_60px_rgba(0,0,0,0.2)]">
            <Image
              src={media.logo}
              alt="Peaceway Pharmacy"
              width={900}
              height={420}
              className="w-full rounded-[1.1rem] bg-white/95 p-7"
            />
          </div>

          <div className="glass rounded-[1.6rem] p-6 md:p-7">
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-white/55">Best next step</p>
            <p className="text-sm leading-7 text-white/78">
              Start on Telegram for ordering, then use the contact channels below for follow-up and general questions.
            </p>
          </div>
        </div>

        <div className="glass rounded-[1.6rem] p-5 md:p-7">
          <div className="grid gap-4 sm:grid-cols-2">
            {contacts.map(([label, value, href], index) => (
              <div
                key={label}
                className={`rounded-[1.2rem] border p-4 transition-colors ${
                  index === 1 || index === 2
                    ? "border-emerald-500/20 bg-emerald-500/8"
                    : "border-white/10 bg-white/5"
                }`}
              >
                <span className="text-[10.5px] uppercase tracking-[0.16em] text-white/45">{label}</span>
                <a
                  href={href}
                  target={href.startsWith("http") ? "_blank" : undefined}
                  rel={href.startsWith("http") ? "noreferrer noopener" : undefined}
                  className="mt-2 block text-sm font-medium leading-6 text-white/88 safe-link"
                >
                  {value}
                </a>
              </div>
            ))}
          </div>
          <p className="mt-6 text-xs leading-6 text-white/45">
            Telegram remains the primary ordering path.
          </p>
        </div>
      </div>
    </SectionShell>
  );
}
