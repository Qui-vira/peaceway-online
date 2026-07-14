import Image from "next/image";
import type { ReactNode } from "react";
import { ScrollSequence } from "@/components/ui/scroll-sequence";
import { HeroContent } from "@/components/ui/hero-content";
import {
  TextFX,
  SplitText,
  RotatingWords,
  ScrambleText,
  Marquee,
  MagneticText,
} from "@/components/ui/text-fx";
import {
  Camera,
  Mail,
  MapPin,
  MessageCircle,
  Send,
  SendHorizontal,
  Users
} from "lucide-react";
import { media } from "@/lib/media";
import { siteConfig } from "@/lib/constants";

type IconBadgeProps = {
  children: ReactNode;
  className?: string;
};

function IconBadge({ children, className = "" }: IconBadgeProps): JSX.Element {
  return <div className={className}>{children}</div>;
}

export default function Page(): JSX.Element {
  return (
    <>
      <header id="nav">
        <div className="ni">
          <a href="#s1">
            <Image className="nlogo" src={media.logo} alt="Peaceway Pharmacy" width={120} height={48} priority />
          </a>
          <div className="nlinks">
            <a className="nl" href="#s2">About</a>
            <a className="nl" href="#s3">Services</a>
            <a className="nl" href="#s5">How It Works</a>
            <a className="nl" href="#s7">Delivery</a>
            <a className="nl" href="#s9">Contact</a>
          </div>
          <div className="flex items-center gap-3">
            <a className="ncta" href="/app">
              <MagneticText>Use Web App</MagneticText>
            </a>
          </div>
        </div>
      </header>

      <main id="lmain">
        <div id="spbar"><div id="spfill" /></div>
        <div className="pw-dots" aria-label="Landing sections">
          {Array.from({ length: 10 }).map((_, index) => (
            <button
              key={index}
              type="button"
              className={`pw-dot${index === 0 ? " is-active" : ""}`}
              aria-label={`Go to section ${index + 1}`}
            />
          ))}
        </div>

        <div className="scene" id="s1" style={{ height: "190vh" }}>
          <div className="sticky" data-screen-label="Hero">
            <div className="sv-fb" />
            <div className="hstage" aria-hidden="true" />
            <ScrollSequence sceneId="s1" />
            <div className="grg" />
            <div className="ovg" />
            <div className="vign" />
            <div className="snbg" aria-hidden="true">01</div>
            <div className="hscrim" aria-hidden="true" />
            <HeroContent />
          </div>
        </div>

        <div className="scene" id="s2" style={{ height: "155vh" }}>
          <div className="sticky" data-screen-label="The Problem">
            <div className="sv-fb" />
            <div className="ov" style={{ background: "rgba(7,8,6,.72)" }} />
            <div style={{ position: "absolute", inset: 0, background: "linear-gradient(to bottom,rgba(7,8,6,.6) 0%,rgba(40,4,8,.2) 50%,rgba(7,8,6,.96) 100%)", zIndex: 1, pointerEvents: "none" }} />
            <div className="vign" />
            <div className="snbg" aria-hidden="true">02</div>
            <div className="con">
              <TextFX as="div" effect="slide-left" className="stag">Section 02</TextFX>
              <SplitText as="h2" effect="mask-words" className="shead" style={{ maxWidth: "700px" }} text="Buying medicine should not feel like guessing." />
              <p className="ssub">In Lagos, getting the right medicine can feel risky. Wrong advice, fake products, and unnecessary movement should not be part of healthcare.</p>
              <div className="g3">
                <div className="pc">
                  <div className="ic-r">!</div>
                  <div className="cn2">Wrong advice from unqualified sources</div>
                  <div className="cd">Street sellers and unqualified vendors regularly provide dangerous medication guidance with no accountability.</div>
                </div>
                <div className="pc">
                  <div className="ic-r">!</div>
                  <div className="cn2">Counterfeit and substandard medicines</div>
                  <div className="cd">Without a licensed pharmacy you cannot verify the source, quality, or safety of what you are buying.</div>
                </div>
                <div className="pc">
                  <div className="ic-r">!</div>
                  <div className="cn2">Unnecessary movement across Lagos</div>
                  <div className="cd">Getting medicine should not mean hours in traffic. A working pharmacy model should bring medicine to you.</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="scene" id="s3" style={{ height: "200vh" }}>
          <div className="sticky" data-screen-label="Services">
            <div className="sv-fb" />
            <div className="ov" />
            <div className="ovg" />
            <div className="vign" />
            <div className="snbg" aria-hidden="true">03</div>
            <div className="con">
              <TextFX as="div" effect="slide-right" className="stag">Section 03 · What We Do</TextFX>
              <SplitText as="h2" effect="lines" className="shead" text={"Order medicine. Ask a pharmacist.\nGet it delivered."} />
              <div className="g3" style={{ marginTop: "8px" }}>
                <div className="gc"><div className="ic-g">+</div><div className="cn2">OTC Medicine Delivery</div><div className="cd">Order over-the-counter medicines directly through Telegram. Availability confirmed before you pay.</div></div>
                <div className="gc"><div className="ic-g">+</div><div className="cn2">Pharmacist Questions via Telegram</div><div className="cd">Ask a pharmacist directly through our bot before ordering. Get proper, qualified guidance.</div></div>
                <div className="gc"><div className="ic-g">+</div><div className="cn2">Product Availability Check</div><div className="cd">We verify stock before confirming your order. No surprises, no delays on unavailable items.</div></div>
                <div className="gc"><div className="ic-g">+</div><div className="cn2">Prescription Review Where Required</div><div className="cd">Prescription-only medicines require pharmacist review before supply. We take this seriously.</div></div>
                <div className="gc"><div className="ic-g">+</div><div className="cn2">Delivery Across Selected Lagos Areas</div><div className="cd">Starting from Igando. Covering Agodo, Ikotun, Egbeda, Idimu, Iyana Ipaja, Egbe, Ejigbo, and more.</div></div>
                <div className="gc"><div className="ic-g">+</div><div className="cn2">Customer Support and Follow-up</div><div className="cd">We check in after every delivery to confirm you received the right product and that all is in order.</div></div>
              </div>
            </div>
          </div>
        </div>

        <div className="scene" id="s4" style={{ height: "165vh" }}>
          <div className="sticky" data-screen-label="Why Trust Peaceway">
            <div className="sv-fb" />
            <div className="ov" />
            <div className="ovg" />
            <div className="vign" />
            <div className="snbg" aria-hidden="true">04</div>
            <div className="con">
              <div className="g2">
                <div>
                  <Image className="phimg" src={media.pharmacyPhoto} alt="Peaceway Pharmacy, Igando Lagos" width={1400} height={900} />
                </div>
                <div>
                  <TextFX as="div" effect="fade-up" className="stag">Section 04 · Why Trust Us</TextFX>
                  <TextFX as="h2" effect="blur" className="shead">A real pharmacy behind the online service.</TextFX>
                  <p style={{ fontSize: 14, color: "var(--m)", lineHeight: 1.7, marginBottom: 20 }}>Peaceway Online is not a startup guessing at healthcare. It is a real, physical pharmacy extending its service online.</p>
                  <div className="titem"><div className="tdot"><div className="tdi" /></div><div><div className="tt">Physical pharmacy in Igando/Agodo Ikotun</div><div className="tb">A real building, real address, real staff.</div></div></div>
                  <div className="titem"><div className="tdot"><div className="tdi" /></div><div><div className="tt">Pharmacist-led service</div><div className="tb">Every order and question is handled by qualified pharmacy staff.</div></div></div>
                  <div className="titem"><div className="tdot"><div className="tdi" /></div><div><div className="tt">Genuine, properly sourced medicines</div><div className="tb">Sourced through legitimate supply chains only.</div></div></div>
                  <div className="titem"><div className="tdot"><div className="tdi" /></div><div><div className="tt">Prescription products require pharmacist review</div><div className="tb">No Rx supply without proper review. This is non-negotiable.</div></div></div>
                  <div className="titem" style={{ borderBottom: "none" }}><div className="tdot"><div className="tdi" /></div><div><div className="tt">PCN Registration <span style={{ fontSize: 11, color: "rgba(177,189,176,.45)", fontWeight: 400 }}>[Placeholder - to be confirmed]</span></div><div className="tb">Registered with the Pharmacists Council of Nigeria.</div></div></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="scene" id="s5" style={{ height: "auto" }}>
          <div className="sticky" data-screen-label="How Ordering Works">
            <div className="sv-fb" />
            <div className="ov" />
            <div className="ovg" />
            <div className="vign" />
            <div className="snbg" aria-hidden="true">05</div>
            <div className="con">
              <TextFX as="div" effect="scale-up" className="stag">Section 05 · How It Works</TextFX>
              <SplitText as="h2" effect="letters" className="shead" text="From message to delivery." />
              <p className="ssub">Ten steps. No complicated apps. Just Telegram, a pharmacist, and your door.</p>
              <div className="sgrid">
                {[
                  ["1", "Click Order on Telegram", "Open the Peaceway Online bot to begin."],
                  ["6", "Pay for your order", "Complete payment through the confirmed method."],
                  ["2", "Tell the bot what you need", "Search or describe the medicine you need."],
                  ["7", "Peaceway packages your order", "Medicines properly packed and prepared."],
                  ["3", "Confirm product and quantity", "Review details before proceeding."],
                  ["8", "Logistics partner delivers", "A trusted partner picks up and delivers to you."],
                  ["4", "Enter your delivery area", "Confirm we cover your location."],
                  ["9", "You track the order", "Stay updated via the Telegram bot."],
                  ["5", "Confirm total and delivery fee", "Review final amount before paying."],
                  ["10", "Peaceway follows up", "We check in after delivery to confirm all is well."]
                ].map(([num, title, desc]) => (
                  <div className="sstep" key={title}>
                    <div className="snum">{num}</div>
                    <div><div className="stit">{title}</div><div className="sdesc">{desc}</div></div>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 24 }}><a className="bp" href={siteConfig.telegramBotUrl} target="_blank" rel="noreferrer noopener">Start Your Order</a></div>
            </div>
          </div>
        </div>

        <div className="scene" id="s6" style={{ height: "165vh" }}>
          <div className="sticky" data-screen-label="Ask the Pharmacist">
            <div className="sv-fb" />
            <div className="ov" />
            <div className="ovg" />
            <div className="vign" />
            <div className="snbg" aria-hidden="true">06</div>
            <div className="con">
              <div className="g2">
                <div>
                  <TextFX as="div" effect="slide-left" className="stag">Section 06 · Ask a Pharmacist</TextFX>
                  <SplitText as="h2" effect="flip" className="shead" text="Need help before you buy?" />
                  <p style={{ fontSize: 15, color: "var(--m)", lineHeight: 1.75, maxWidth: 420, marginBottom: 20 }}>Our pharmacist is available through the Telegram bot. Ask questions about medicines, dosage, interactions, or side effects before you order.</p>
                  <p style={{ fontSize: 13, color: "rgba(177,189,176,.55)", maxWidth: 380, lineHeight: 1.65, marginBottom: 32 }}>Prescription-only products require review before supply. This is how we keep you safe.</p>
                  <a className="bp" href={siteConfig.telegramBotUrl} target="_blank" rel="noreferrer noopener">Ask a Pharmacist</a>
                </div>
                <div className="cw">
                  <div className="cb cu2">Is it safe to take paracetamol and ibuprofen together?</div>
                  <div className="cb cp2"><div className="cpn">Peaceway Pharmacist</div>Yes, both can be taken together, but space them 4 to 6 hours apart to reduce stomach irritation, and ulcer patients should avoid ibuprofen. Avoid taking them at the exact same time.</div>
                  <div className="cb cu2">I need to refill my blood pressure medication.</div>
                  <div className="cb cp2"><div className="cpn">Peaceway Pharmacist</div>Antihypertensive medicines require a prescription. Send your prescription through the bot and I will guide you through the next steps.</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="scene" id="s7" style={{ height: "160vh" }}>
          <div className="sticky" data-screen-label="Delivery Areas">
            <div className="sv-fb" />
            <div className="ov" />
            <div className="ovg" />
            <div className="vign" />
            <div className="snbg" aria-hidden="true">07</div>
            <div className="con">
              <div className="g2" style={{ alignItems: "flex-start" }}>
                <div>
                  <TextFX as="div" effect="scale-down" className="stag">Section 07 · Delivery Areas</TextFX>
                  <SplitText as="h2" effect="lines" className="shead" text={"Delivery across Lagos,\nstarting from Igando."} />
                  <p style={{ fontSize: 15, color: "var(--m)", lineHeight: 1.7, maxWidth: 420, marginBottom: 32 }}>We deliver to communities around our pharmacy first. Coverage is expanding. If your area is not listed, ask us.</p>
                  <div className="ag">
                    {["Igando ★", "Agodo", "Ikotun", "Egbeda", "Isheri", "Idimu", "Iyana Ipaja", "Egbe", "Ejigbo", "Ijegun", "Other Lagos Mainland"].map((label, index) => (
                      <span key={label} className={index < 3 ? "ab pri" : "ab sec"}>{label}</span>
                    ))}
                  </div>
                  <p style={{ fontSize: 12, color: "rgba(177,189,176,.4)", marginTop: 18, lineHeight: 1.6 }}>★ Primary delivery zones around Igando/Agodo Ikotun. Fees vary by location.</p>
                </div>
                <div>
                  <svg viewBox="0 0 320 280" width="100%" style={{ maxWidth: 320, display: "block" }} fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M28 250 Q48 222 76 205 Q106 187 144 177 Q178 170 210 175 Q242 180 270 163 Q292 149 302 127 Q297 90 278 64 Q256 36 222 28 Q188 20 156 32 Q124 44 100 66 Q76 88 58 114 Q40 138 32 168 Z" fill="rgba(15,103,60,0.06)" stroke="rgba(15,103,60,0.18)" strokeWidth="1.5" />
                    <circle cx="138" cy="195" r="16" fill="rgba(15,103,60,0.2)" stroke="#0F673C" strokeWidth="1.5" />
                    <circle cx="138" cy="195" r="5" fill="#0F673C" />
                    <circle cx="138" cy="195" r="26" fill="rgba(15,103,60,0.08)">
                      <animate attributeName="r" from="16" to="32" dur="2.5s" repeatCount="indefinite" />
                      <animate attributeName="opacity" from="0.3" to="0" dur="2.5s" repeatCount="indefinite" />
                    </circle>
                    <text x="156" y="200" fontSize="11" fill="#0F673C" fontFamily="DM Sans,sans-serif" fontWeight="700">Igando</text>
                    <circle cx="162" cy="172" r="5" fill="rgba(15,103,60,0.45)" stroke="#0F673C" strokeWidth="1" />
                    <text x="170" y="176" fontSize="9" fill="rgba(177,189,176,0.65)" fontFamily="DM Sans,sans-serif">Agodo</text>
                    <circle cx="108" cy="215" r="5" fill="rgba(15,103,60,0.4)" stroke="rgba(15,103,60,0.6)" strokeWidth="1" />
                    <text x="116" y="219" fontSize="9" fill="rgba(177,189,176,0.65)" fontFamily="DM Sans,sans-serif">Ikotun</text>
                    <circle cx="198" cy="163" r="4" fill="rgba(177,189,176,0.2)" stroke="rgba(177,189,176,0.3)" strokeWidth="1" />
                    <text x="206" y="167" fontSize="8.5" fill="rgba(177,189,176,0.5)" fontFamily="DM Sans,sans-serif">Egbeda</text>
                    <circle cx="88" cy="180" r="4" fill="rgba(177,189,176,0.2)" stroke="rgba(177,189,176,0.3)" strokeWidth="1" />
                    <text x="96" y="184" fontSize="8.5" fill="rgba(177,189,176,0.5)" fontFamily="DM Sans,sans-serif">Idimu</text>
                    <circle cx="236" cy="145" r="4" fill="rgba(177,189,176,0.2)" stroke="rgba(177,189,176,0.3)" strokeWidth="1" />
                    <text x="244" y="149" fontSize="8.5" fill="rgba(177,189,176,0.5)" fontFamily="DM Sans,sans-serif">Ejigbo</text>
                    <text x="86" y="258" fontSize="10.5" fill="rgba(177,189,176,0.35)" fontFamily="DM Sans,sans-serif">Lagos State, Nigeria</text>
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="scene" id="s8" style={{ height: "145vh" }}>
          <div className="sticky" data-screen-label="Community">
            <div className="sv-fb" />
            <div className="ov" />
            <div className="ovg" />
            <div className="vign" />
            <div className="grg" />
            <div className="snbg" aria-hidden="true">08</div>
            <div className="con" style={{ alignItems: "center", textAlign: "center" }}>
              <TextFX as="div" effect="fade-in" className="stag">Section 08 · Community</TextFX>
              <h2 className="shead" style={{ maxWidth: 620, margin: "0 auto 12px" }}>
                Join the Peaceway{" "}
                <RotatingWords words={["health", "care", "wellness"]} className="fx-gradient" /> community.
              </h2>
              <p style={{ fontSize: 15, color: "var(--m)", maxWidth: 440, margin: "0 auto 44px", lineHeight: 1.7 }}>Stay informed. Get health tips. Ask questions. Be part of a growing Lagos health community.</p>
              <div style={{ display: "flex", flexDirection: "column", gap: 16, width: "100%", maxWidth: 620 }}>
                <a className="tgcard tgc1" href={siteConfig.telegramChannelUrl} target="_blank" rel="noreferrer noopener">
                  <IconBadge
                    className="icon-badge icon-badge-green"
                  >
                    <Users size={22} strokeWidth={2} />
                  </IconBadge>
                  <div style={{ textAlign: "left" }}><div className="tgct">Join Telegram Channel</div><div className="tgcd">Health updates, product alerts, pharmacy news, and community information, direct to your Telegram.</div></div>
                  <div style={{ marginLeft: "auto", fontSize: 20, color: "var(--g)", flexShrink: 0 }}>→</div>
                </a>
                <a className="tgcard tgc2" href={siteConfig.telegramBotUrl} target="_blank" rel="noreferrer noopener">
                  <IconBadge
                    className="icon-badge icon-badge-neutral"
                  >
                    <SendHorizontal size={22} strokeWidth={2} />
                  </IconBadge>
                  <div style={{ textAlign: "left" }}><div className="tgct">Order on Telegram Bot</div><div className="tgcd">Place orders, ask pharmacist questions, check availability, and track delivery, all in one bot.</div></div>
                  <div style={{ marginLeft: "auto", fontSize: 20, color: "var(--m)", flexShrink: 0 }}>→</div>
                </a>
              </div>
            </div>
          </div>
        </div>

        <div className="scene" id="s9" style={{ height: "145vh" }}>
          <div className="sticky" data-screen-label="Contact">
            <div className="sv-fb" />
            <div className="ov" />
            <div className="ovg" />
            <div className="vign" />
            <div className="snbg" aria-hidden="true">09</div>
            <div className="con">
              <div className="g2" style={{ alignItems: "flex-start" }}>
                <div>
                  <TextFX as="div" effect="fade-up" className="stag">Section 09 · Contact</TextFX>
                  <h2 className="shead"><ScrambleText text="Talk to Peaceway." /></h2>
                  <p style={{ fontSize: 15, color: "var(--m)", maxWidth: 380, lineHeight: 1.75, marginBottom: 16 }}>We are a real pharmacy with real people. Reach us through any of the channels below.</p>
                  <p style={{ fontSize: 13, color: "rgba(177,189,176,.5)", maxWidth: 360, lineHeight: 1.65 }}>For orders, use the Telegram bot. For general inquiries or pharmacist questions, any channel works.</p>
                </div>
                <div className="ctcard">
                  <div className="ctitem"><div className="ctico"><Mail size={18} strokeWidth={2} /></div><div><div className="ctlb">Email</div><div className="ctva">{siteConfig.email}</div></div></div>
                  <div className="ctitem"><div className="ctico"><Send size={18} strokeWidth={2} /></div><div><div className="ctlb">Telegram Bot</div><a className="ctva" href={siteConfig.telegramBotUrl} target="_blank" rel="noreferrer noopener" style={{ color: "var(--t)" }}>t.me/Peacewayonline_bot</a></div></div>
                  <div className="ctitem"><div className="ctico"><Send size={18} strokeWidth={2} /></div><div><div className="ctlb">Telegram Channel</div><a className="ctva" href={siteConfig.telegramChannelUrl} target="_blank" rel="noreferrer noopener" style={{ color: "var(--t)" }}>t.me/peacewayonline</a></div></div>
                  <div className="ctitem"><div className="ctico"><MapPin size={18} strokeWidth={2} /></div><div><div className="ctlb">Address</div><div className="ctva">Peaceway Pharmacy, Igando/Agodo Ikotun, Lagos</div></div></div>
                  <div className="ctitem"><div className="ctico"><Camera size={18} strokeWidth={2} /></div><div><div className="ctlb">Instagram</div><a className="ctva" href={siteConfig.instagramUrl} target="_blank" rel="noreferrer noopener" style={{ color: "var(--t)" }}>@peacewayonline</a></div></div>
                  <div className="ctitem"><div className="ctico"><MessageCircle size={18} strokeWidth={2} /></div><div><div className="ctlb">WhatsApp</div><div className="ctva" style={{ color: "rgba(177,189,176,.45)" }}>[Placeholder - to be added]</div></div></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      {/* Footer lives inside main so it becomes the last slide in the
          mobile carousel; on desktop it flows after the scenes as before. */}
      <footer className="ft" id="footer" data-screen-label="Footer">
        <div className="ft-marquee" aria-hidden="true">
          <Marquee speed={34}>
            {["Genuine medicines", "Pharmacist-led guidance", "Delivery across Lagos", "A real Igando pharmacy", "Prescription review"].map((t) => (
              <span key={t} className="ft-marquee-item">
                {t}
                <span className="ft-marquee-dot">✦</span>
              </span>
            ))}
          </Marquee>
        </div>
        <div style={{ maxWidth: 1240, margin: "0 auto", padding: "0 56px" }}>
          <div className="fg">
            <div>
              <Image className="flogo" src={media.logo} alt="Peaceway Pharmacy" width={180} height={72} />
              <div className="fbd">Peaceway Online</div>
              <div className="fbs">An online extension of Peaceway Pharmacy, Igando/Agodo Ikotun, Lagos, Nigeria.</div>
              <div className="fsa">
                <a className="fsi" href={siteConfig.telegramChannelUrl} target="_blank" rel="noreferrer noopener" aria-label="Telegram Channel"><Send size={16} strokeWidth={2} /></a>
                <a className="fsi" href={siteConfig.instagramUrl} target="_blank" rel="noreferrer noopener" aria-label="Instagram"><Camera size={16} strokeWidth={2} /></a>
                <a className="fsi" href="#" aria-label="WhatsApp placeholder"><MessageCircle size={16} strokeWidth={2} /></a>
                <a className="fsi" href="#" aria-label="Facebook placeholder"><Users size={16} strokeWidth={2} /></a>
              </div>
            </div>
            <div>
              <div className="fct">Services</div>
              <a className="fl" href={siteConfig.telegramBotUrl} target="_blank" rel="noreferrer noopener">OTC Medicine Delivery</a>
              <a className="fl" href="/request">Check Availability</a>
              <a className="fl" href={siteConfig.telegramBotUrl} target="_blank" rel="noreferrer noopener">Ask a Pharmacist</a>
              <a className="fl" href="#s7">Delivery Areas</a>
              <a className="fl" href="#s5">How It Works</a>
              <a className="fl" href="#s4">Prescription Review</a>
            </div>
            <div>
              <div className="fct">Connect</div>
              <a className="fl" href={siteConfig.telegramBotUrl} target="_blank" rel="noreferrer noopener">Telegram Bot</a>
              <a className="fl" href={siteConfig.telegramChannelUrl} target="_blank" rel="noreferrer noopener">Telegram Channel</a>
              <a className="fl" href={siteConfig.instagramUrl} target="_blank" rel="noreferrer noopener">Instagram</a>
              <a className="fl" href="#" style={{ opacity: 0.45 }}>WhatsApp [Soon]</a>
              <a className="fl" href="#" style={{ opacity: 0.45 }}>Facebook [Soon]</a>
            </div>
            <div>
              <div className="fct">Legal</div>
              <a className="fl" href="#">Privacy Policy</a>
              <a className="fl" href="#">Terms &amp; Conditions</a>
              <a className="fl" href="#">Refund &amp; Delivery Policy</a>
              <a className="fl" href="#s4">About Peaceway</a>
            </div>
          </div>
          <div className="fdiv" />
          <div className="fleg">
            <p>PCN Registration: [Placeholder - to be confirmed] | Peaceway Pharmacy, Igando/Agodo Ikotun, Lagos, Nigeria | {siteConfig.email}</p>
            <p style={{ marginTop: 6 }}>&copy; 2026 Peaceway Online. All rights reserved. Peaceway Online is an online service of Peaceway Pharmacy.</p>
            <p style={{ marginTop: 6 }}>Prescription-only medicines require a valid prescription and pharmacist review before supply. This website does not provide medical diagnosis or treatment advice.</p>
          </div>
        </div>
      </footer>
      </main>
    </>
  );
}
