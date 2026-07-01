import Image from "next/image";
import { media } from "@/lib/media";
import { siteConfig } from "@/lib/constants";

export function FooterSection(): JSX.Element {
  return (
    <footer className="relative z-10 border-t border-white/10 bg-bgd py-16">
      <div className="mx-auto max-w-[1240px] px-5 md:px-14">
        <div className="grid gap-12 lg:grid-cols-[1.5fr_1fr_1fr_1fr]">
          <div>
            <Image src={media.logo} alt="Peaceway Pharmacy" width={180} height={72} className="mb-4 h-10 w-auto rounded-md bg-white/95 p-1.5" />
            <div className="mb-4 text-[15px] font-extrabold text-white">Peaceway Online</div>
            <p className="mb-4 max-w-[220px] text-[12px] leading-6 text-[#B1BDB0]">
              An online extension of Peaceway Pharmacy, Igando/Agodo Ikotun, Lagos, Nigeria.
            </p>
            <div className="flex gap-2 flex-wrap">
              <a className="inline-flex items-center justify-center rounded-full bg-g px-4 py-2 text-[12px] font-semibold uppercase tracking-[0.08em] text-white" href={siteConfig.telegramBotUrl} target="_blank" rel="noreferrer noopener">
                Order on Telegram
              </a>
              <a className="safe-link text-[12px]" href={siteConfig.telegramChannelUrl} target="_blank" rel="noreferrer noopener">
                Telegram Channel
              </a>
              <a className="safe-link text-[12px]" href={siteConfig.instagramUrl} target="_blank" rel="noreferrer noopener">
                Instagram
              </a>
            </div>
          </div>

          <div>
            <div className="mb-4 text-[11px] font-bold uppercase tracking-[0.1em] text-g">Services</div>
            <div className="space-y-3 text-[13px] text-[#B1BDB0]">
              <a className="block safe-link" href={siteConfig.telegramBotUrl} target="_blank" rel="noreferrer noopener">OTC Medicine Delivery</a>
              <a className="block safe-link" href={siteConfig.telegramBotUrl} target="_blank" rel="noreferrer noopener">Ask a Pharmacist</a>
              <a className="block safe-link" href="#delivery">Delivery Areas</a>
              <a className="block safe-link" href="#how-it-works">How It Works</a>
              <a className="block safe-link" href="#pharmacist">Prescription Review</a>
            </div>
          </div>

          <div>
            <div className="mb-4 text-[11px] font-bold uppercase tracking-[0.1em] text-g">Connect</div>
            <div className="space-y-3 text-[13px] text-[#B1BDB0]">
              <a className="block safe-link" href={siteConfig.telegramBotUrl} target="_blank" rel="noreferrer noopener">Telegram Bot</a>
              <a className="block safe-link" href={siteConfig.telegramChannelUrl} target="_blank" rel="noreferrer noopener">Telegram Channel</a>
              <a className="block safe-link" href={siteConfig.instagramUrl} target="_blank" rel="noreferrer noopener">Instagram</a>
              <span className="block opacity-45">WhatsApp [Soon]</span>
              <span className="block opacity-45">Facebook [Soon]</span>
            </div>
          </div>

          <div>
            <div className="mb-4 text-[11px] font-bold uppercase tracking-[0.1em] text-g">Legal</div>
            <div className="space-y-3 text-[13px] text-[#B1BDB0]">
              <a className="block safe-link" href="#">Privacy Policy</a>
              <a className="block safe-link" href="#">Terms &amp; Conditions</a>
              <a className="block safe-link" href="#">Refund &amp; Delivery Policy</a>
              <a className="block safe-link" href="#trust">About Peaceway</a>
            </div>
          </div>
        </div>

        <div className="my-6 h-px bg-white/10" />
        <div className="space-y-1 text-[11.5px] leading-6 text-white/45">
          <p>PCN Registration: [Placeholder - to be confirmed] | Peaceway Pharmacy, Igando/Agodo Ikotun, Lagos, Nigeria | {siteConfig.email}</p>
          <p>&copy; 2026 Peaceway Online. All rights reserved. Peaceway Online is an online service of Peaceway Pharmacy.</p>
          <p>Prescription-only medicines require a valid prescription and pharmacist review before supply. This website does not provide medical diagnosis or treatment advice.</p>
        </div>
      </div>
    </footer>
  );
}
