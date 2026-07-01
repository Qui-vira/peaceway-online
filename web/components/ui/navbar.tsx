import Image from "next/image";
import { navLinks, siteConfig } from "@/lib/constants";
import { media } from "@/lib/media";

export function Navbar(): JSX.Element {
  return (
    <header className="fixed left-0 top-0 z-50 w-full border-b border-transparent bg-[rgba(9,10,7,0.75)] backdrop-blur-xl transition-[background,border-color] duration-300">
      <div className="mx-auto flex max-w-[1240px] items-center justify-between px-5 py-[18px] md:px-14">
        <a href="#hero" className="flex items-center gap-3">
          <Image
            src={media.logo}
            alt="Peaceway Pharmacy"
            width={120}
            height={48}
            className="h-9 w-auto rounded-[7px] bg-white/95 px-2 py-1"
            priority
          />
          <span className="hidden text-[12.5px] uppercase tracking-[0.1em] text-white/60 lg:inline">
            Peaceway Online
          </span>
        </a>

        <nav className="hidden items-center gap-9 lg:flex" aria-label="Primary">
          {navLinks.map((link) => (
            <a key={link.href} href={link.href} className="text-[12.5px] font-medium uppercase tracking-[0.1em] text-white/60 safe-link">
              {link.label}
            </a>
          ))}
        </nav>

        <a
          href={siteConfig.telegramBotUrl}
          target="_blank"
          rel="noreferrer noopener"
          className="inline-flex items-center rounded-[22px] bg-g px-6 py-2.5 text-[12px] font-semibold uppercase tracking-[0.08em] text-white transition hover:bg-g2"
        >
          Order on Telegram
        </a>
      </div>
    </header>
  );
}
