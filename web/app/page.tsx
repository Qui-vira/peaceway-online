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
import { compliance, siteConfig } from "@/lib/constants";
import { RegulatoryNotice } from "@/components/brand/regulatory-notice";

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
            <a className="nl" href="#s7">Sourcing</a>
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

        <div className="scene" id="s1" style={{ height: "190vh" }}>
          <div className="pw-sticky" data-screen-label="Hero">
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
          <div className="pw-sticky" data-screen-label="The Problem">
            <div className="sv-fb" />
            <div className="ov" style={{ background: "rgba(7,8,6,.72)" }} />
            <div style={{ position: "absolute", inset: 0, background: "linear-gradient(to bottom,rgba(7,8,6,.6) 0%,rgba(40,4,8,.2) 50%,rgba(7,8,6,.96) 100%)", zIndex: 1, pointerEvents: "none" }} />
            <div className="vign" />
            <div className="snbg" aria-hidden="true">02</div>
            <div className="con">
              <SplitText as="h2" effect="mask-words" className="shead" style={{ maxWidth: "700px" }} text="Most medicine is bought without a pharmacist involved." />
              <p className="ssub">Counterfeit and substandard medicine circulates in Nigeria. Wrong advice and unverified products should not be part of healthcare.</p>
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
                  <div className="cn2">No pharmacist involved</div>
                  <div className="cd">Most medicine online is sold without a pharmacist reviewing what is being bought, or who is buying it.</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="scene" id="s3" style={{ height: "200vh" }}>
          <div className="pw-sticky" data-screen-label="Services">
            <div className="sv-fb" />
            <div className="ov" />
            <div className="ovg" />
            <div className="vign" />
            <div className="snbg" aria-hidden="true">03</div>
            <div className="con">
              <SplitText as="h2" effect="lines" className="shead" text={"Dispensing, with a pharmacist\non every order."} />
              <div className="g3" style={{ marginTop: "8px" }}>
                <div className="gc"><div className="ic-g">+</div><div className="cn2">Pharmacist Review On Every Order</div><div className="cd">A registered pharmacist checks each order before it is dispensed. Stock is confirmed before you pay.</div></div>
                <div className="gc"><div className="ic-g">+</div><div className="cn2">NAFDAC-Registered Medicine</div><div className="cd">Registration is checked before an item is listed. Sourced through licensed distributors only.</div></div>
                <div className="gc"><div className="ic-g">+</div><div className="cn2">Product Availability Check</div><div className="cd">We verify stock before confirming your order. No surprises, no delays on unavailable items.</div></div>
                <div className="gc"><div className="ic-g">+</div><div className="cn2">Prescription Handling</div><div className="cd">Prescriptions are reviewed by our Superintendent Pharmacist. Prescription-only medicine is not supplied without one.</div></div>
                <div className="gc"><div className="ic-g">+</div><div className="cn2">Clear Pricing</div><div className="cd">The price shown is the price charged. Delivery, where it applies, is itemised before you pay.</div></div>
                <div className="gc"><div className="ic-g">+</div><div className="cn2">Follow-Up After Dispensing</div><div className="cd">We check that you received the right medicine and that you know how to take it.</div></div>
              </div>
            </div>
          </div>
        </div>

        <div className="scene" id="s4" style={{ height: "165vh" }}>
          <div className="pw-sticky" data-screen-label="Why Trust Peaceway">
            <div className="sv-fb" />
            <div className="ov" />
            <div className="ovg" />
            <div className="vign" />
            <div className="snbg" aria-hidden="true">04</div>
            <div className="con">
              <div className="g2">
                <div>
                  <Image className="phimg" src={media.pharmacyPhoto} alt="The Peaceway Pharmacy dispensary" width={1400} height={900} />
                </div>
                <div>
                  <TextFX as="h2" effect="blur" className="shead">A real pharmacy behind the online service.</TextFX>
                  <p style={{ fontSize: 14, color: "var(--m)", lineHeight: 1.7, marginBottom: 20 }}>Peaceway Online is operated by Peaceway Pharmacy, a PCN-registered premises with a Superintendent Pharmacist on record. The dispensary is the business; the website is how you reach it.</p>
                  <div className="titem"><div className="tdot"><div className="tdi" /></div><div><div className="tt">A registered physical premises</div><div className="tb">PCN-registered, with a Superintendent Pharmacist on record.</div></div></div>
                  <div className="titem"><div className="tdot"><div className="tdi" /></div><div><div className="tt">Pharmacist-led service</div><div className="tb">Every order and question is handled by qualified pharmacy staff.</div></div></div>
                  <div className="titem"><div className="tdot"><div className="tdi" /></div><div><div className="tt">Genuine, properly sourced medicines</div><div className="tb">Sourced through legitimate supply chains only.</div></div></div>
                  <div className="titem"><div className="tdot"><div className="tdi" /></div><div><div className="tt">Prescription products require pharmacist review</div><div className="tb">No Rx supply without proper review. This is non-negotiable.</div></div></div>
                  {/* Reads from `compliance` so this cannot say "registered"
                      with a bracketed placeholder beside it. Until a number is
                      issued the line states the application is in progress,
                      which is the true position. */}
                  <div className="titem" style={{ borderBottom: "none" }}><div className="tdot"><div className="tdi" /></div><div><div className="tt">Online pharmacy licence <span style={{ fontSize: 11, color: "var(--m2)", fontWeight: 400 }}>{compliance.pharmacyLicenceNumber ?? compliance.pendingLabel}</span></div><div className="tb">Regulated by the Pharmacists Council of Nigeria. Full disclosures are set out at the foot of this page.</div></div></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="scene" id="s5" style={{ height: "auto" }}>
          <div className="pw-sticky" data-screen-label="How Ordering Works">
            <div className="sv-fb" />
            <div className="ov" />
            <div className="ovg" />
            <div className="vign" />
            <div className="snbg" aria-hidden="true">05</div>
            <div className="con">
              <SplitText as="h2" effect="letters" className="shead" text="Order, review, dispense." />
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
                  ["9", "You track the order", "Status updates as the order moves."],
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
          <div className="pw-sticky" data-screen-label="Ask the Pharmacist">
            <div className="sv-fb" />
            <div className="ov" />
            <div className="ovg" />
            <div className="vign" />
            <div className="snbg" aria-hidden="true">06</div>
            <div className="con">
              <div className="g2">
                <div>
                  <SplitText as="h2" effect="flip" className="shead" text="Speak to a pharmacist before you buy." />
                  <p style={{ fontSize: 15, color: "var(--m)", lineHeight: 1.75, maxWidth: 420, marginBottom: 20 }}>A registered pharmacist answers questions about medicines, interactions, and whether an item needs a prescription. Ask questions about medicines, dosage, interactions, or side effects before you order.</p>
                  <p style={{ fontSize: 13, color: "var(--m2)", maxWidth: 380, lineHeight: 1.65, marginBottom: 32 }}>Prescription-only products require review before supply. This is how we keep you safe.</p>
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
          <div className="pw-sticky" data-screen-label="Sourcing">
            <div className="sv-fb" />
            <div className="ov" />
            <div className="ovg" />
            <div className="vign" />
            <div className="snbg" aria-hidden="true">07</div>
            <div className="con">
              <div className="g2" style={{ alignItems: "flex-start" }}>
                <div>
                  {/* This section was a Lagos delivery-coverage map: eleven
                      neighbourhood chips and an SVG with a pulsing dot over
                      Igando. It framed the business as a courier with a
                      service radius, and it capped the proposition at one
                      city on the most-scrolled part of the page. What a
                      customer buying medicine online actually needs to know is
                      where the medicine came from. Delivery areas still exist -
                      priced per zone at checkout, which is where a fulfilment
                      detail belongs. */}
                  <SplitText as="h2" effect="lines" className="shead" text={"Traceable to a\nlicensed supplier."} />
                  <p style={{ fontSize: 15, color: "var(--m)", lineHeight: 1.7, maxWidth: 420, marginBottom: 32 }}>Counterfeit and substandard medicine circulates in Nigeria. The defence against it is not a promise. It is a supply chain you can name.</p>
                  <div className="titem"><div className="tdot"><div className="tdi" /></div><div><div className="tt">Licensed distributors only</div><div className="tb">Stock is bought through licensed distribution channels, never open markets.</div></div></div>
                  <div className="titem"><div className="tdot"><div className="tdi" /></div><div><div className="tt">NAFDAC registration checked</div><div className="tb">Registration is verified before an item is listed for sale.</div></div></div>
                  <div className="titem"><div className="tdot"><div className="tdi" /></div><div><div className="tt">Batch and expiry recorded</div><div className="tb">Held against the dispensing record for every order.</div></div></div>
                  <div className="titem" style={{ borderBottom: "none" }}><div className="tdot"><div className="tdi" /></div><div><div className="tt">Pharmacist sign-off</div><div className="tb">Nothing leaves the dispensary without a pharmacist check.</div></div></div>
                </div>
                <div>
                  <Image className="phimg" src={media.pharmacyPhoto} alt="Medicine shelves inside the Peaceway Pharmacy dispensary" width={1400} height={900} />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="scene" id="s8" style={{ height: "auto" }}>
          <div className="pw-sticky" data-screen-label="Community">
            <div className="sv-fb" />
            <div className="ov" />
            <div className="ovg" />
            <div className="vign" />
            <div className="grg" />
            <div className="snbg" aria-hidden="true">08</div>
            <div className="con" style={{ alignItems: "center", textAlign: "center" }}>
              <h2 className="shead" style={{ maxWidth: 620, margin: "0 auto 12px" }}>
                Join the Peaceway{" "}
                <RotatingWords words={["health", "care", "wellness"]} className="fx-gradient" /> community.
              </h2>
              <p style={{ fontSize: 15, color: "var(--m)", maxWidth: 440, margin: "0 auto 44px", lineHeight: 1.7 }}>Stock notices, medicine safety information, and answers to common questions. Part of a growing Lagos health community.</p>
              <div style={{ display: "flex", flexDirection: "column", gap: 16, width: "100%", maxWidth: 620 }}>
                <a className="tgcard tgc1" href={siteConfig.telegramChannelUrl} target="_blank" rel="noreferrer noopener">
                  <IconBadge
                    className="icon-badge icon-badge-green"
                  >
                    <Users size={22} strokeWidth={2} />
                  </IconBadge>
                  <div style={{ textAlign: "left" }}><div className="tgct">Join Telegram Channel</div><div className="tgcd">Health updates, product alerts, pharmacy news, and community information, direct to your Telegram.</div></div>
                  <div style={{ marginLeft: "auto", fontSize: 20, color: "var(--g-text)", flexShrink: 0 }}>→</div>
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
          <div className="pw-sticky" data-screen-label="Contact">
            <div className="sv-fb" />
            <div className="ov" />
            <div className="ovg" />
            <div className="vign" />
            <div className="snbg" aria-hidden="true">09</div>
            <div className="con">
              <div className="g2" style={{ alignItems: "flex-start" }}>
                <div>
                  <h2 className="shead"><ScrambleText text="Talk to Peaceway." /></h2>
                  <p style={{ fontSize: 15, color: "var(--m)", maxWidth: 380, lineHeight: 1.75, marginBottom: 16 }}>A registered premises with a Superintendent Pharmacist on record. Reach us through any of the channels below.</p>
                  <p style={{ fontSize: 13, color: "var(--m2)", maxWidth: 360, lineHeight: 1.65 }}>For orders, use the web app or the Telegram bot. For general inquiries or pharmacist questions, any channel works.</p>
                </div>
                <div className="ctcard">
                  <div className="ctitem"><div className="ctico"><Mail size={18} strokeWidth={2} /></div><div><div className="ctlb">Email</div><div className="ctva">{siteConfig.email}</div></div></div>
                  <div className="ctitem"><div className="ctico"><Send size={18} strokeWidth={2} /></div><div><div className="ctlb">Telegram Bot</div><a className="ctva" href={siteConfig.telegramBotUrl} target="_blank" rel="noreferrer noopener" style={{ color: "var(--t)" }}>t.me/Peacewayonline_bot</a></div></div>
                  <div className="ctitem"><div className="ctico"><Send size={18} strokeWidth={2} /></div><div><div className="ctlb">Telegram Channel</div><a className="ctva" href={siteConfig.telegramChannelUrl} target="_blank" rel="noreferrer noopener" style={{ color: "var(--t)" }}>t.me/peacewayonline</a></div></div>
                  <div className="ctitem"><div className="ctico"><MapPin size={18} strokeWidth={2} /></div><div><div className="ctlb">Registered premises</div><div className="ctva">{siteConfig.address}</div></div></div>
                  <div className="ctitem"><div className="ctico"><Camera size={18} strokeWidth={2} /></div><div><div className="ctlb">Instagram</div><a className="ctva" href={siteConfig.instagramUrl} target="_blank" rel="noreferrer noopener" style={{ color: "var(--t)" }}>@peacewayonline</a></div></div>
                  <div className="ctitem"><div className="ctico"><MessageCircle size={18} strokeWidth={2} /></div><div><div className="ctlb">WhatsApp</div><div className="ctva" style={{ color: "var(--m2)" }}>[Placeholder - to be added]</div></div></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      {/* Footer lives inside main so it becomes the last slide in the
          mobile carousel; on desktop it flows after the scenes as before. */}
      {/* Statutory EPSP disclosures. Homepage, above the footer, in the
          server-rendered HTML - a regulator or a crawler must be able to read
          them without running JavaScript. */}
      <RegulatoryNotice />

      <footer className="ft" id="footer" data-screen-label="Footer">
        <div className="ft-marquee" aria-hidden="true">
          <Marquee speed={34}>
            {["NAFDAC-registered medicine", "Pharmacist-reviewed orders", "Traceable sourcing", "PCN-registered premises", "Prescription review"].map((t) => (
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
              <div className="fbs">The online pharmacy service of Peaceway Pharmacy, a PCN-registered premises in Nigeria.</div>
              <div className="fsa">
                <a className="fsi" href={siteConfig.telegramChannelUrl} target="_blank" rel="noreferrer noopener" aria-label="Telegram Channel"><Send size={16} strokeWidth={2} /></a>
                <a className="fsi" href={siteConfig.instagramUrl} target="_blank" rel="noreferrer noopener" aria-label="Instagram"><Camera size={16} strokeWidth={2} /></a>
                {/* Not links until there is somewhere to link to. As anchors
                    with href="#" they were keyboard-focusable, announced as
                    links, and went nowhere. */}
                <span className="fsi fsi-soon" aria-label="WhatsApp — coming soon" role="img"><MessageCircle size={16} strokeWidth={2} /></span>
                <span className="fsi fsi-soon" aria-label="Facebook — coming soon" role="img"><Users size={16} strokeWidth={2} /></span>
              </div>
            </div>
            <div>
              <div className="fct">Services</div>
              <a className="fl" href={siteConfig.telegramBotUrl} target="_blank" rel="noreferrer noopener">OTC Medicine Delivery</a>
              <a className="fl" href="/shop">Shop Medicines</a>
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
              <span className="fl fl-soon">WhatsApp<span className="soon-tag">Soon</span></span>
              <span className="fl fl-soon">Facebook<span className="soon-tag">Soon</span></span>
            </div>
            <div>
              <div className="fct">Legal</div>
              {/* These were `href="#"` - three dead links on a pharmacy that
                  also told customers at checkout they were agreeing to terms of
                  service. Marked pending with the same affordance the social
                  links already use, so nothing dead is clickable and nothing
                  false is claimed, until the real pages exist. */}
              <span className="fl fl-soon">Privacy Policy<span className="soon-tag">Soon</span></span>
              <span className="fl fl-soon">Terms &amp; Conditions<span className="soon-tag">Soon</span></span>
              <span className="fl fl-soon">Refund &amp; Delivery Policy<span className="soon-tag">Soon</span></span>
              <a className="fl" href="#s4">About Peaceway</a>
            </div>
          </div>
          <div className="fdiv" />
          {/* The licence and registration numbers used to be a single inline
              string reading "PCN Registration: [Placeholder - to be confirmed]".
              A bracketed placeholder shipped to production reads, to anyone who
              is not the developer, as a registration that exists and simply is
              not typed out. The disclosures now come from `compliance` in
              lib/constants.ts, where an unissued number is `null` and renders as
              "Application in progress" - see RegulatoryNotice. */}
          <div className="fleg">
            <p>{siteConfig.address} | {siteConfig.email}</p>
            <p style={{ marginTop: 6 }}>&copy; 2026 Peaceway Online. All rights reserved. {siteConfig.footerNote}</p>
            <p style={{ marginTop: 6 }}>{compliance.prescriptionDeclaration}</p>
            <p style={{ marginTop: 6 }}>This website does not provide medical diagnosis or treatment advice. For urgent symptoms, seek medical care in person.</p>
          </div>
        </div>
      </footer>
      </main>
    </>
  );
}
