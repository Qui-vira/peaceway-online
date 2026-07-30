"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import {
  ArrowLeft,
  Bell,
  Home,
  MessageCircle,
  ShoppingCart,
  Store,
  User,
} from "lucide-react";
import { getCart } from "@/lib/cart";
import { media } from "@/lib/media";
import { siteConfig } from "@/lib/constants";
import { OfflineBanner } from "@/components/app/offline-banner";

/**
 * Five destinations plus the cart, which is the documented ceiling.
 *
 * "Shop" replaces "Requests" here. The catalogue is how the product makes
 * money and it was the one commercial surface with no nav slot - reachable only
 * from a card on the home screen or a link in the footer - while Requests, the
 * slower "ask us to find it" path, had one. Requests has not gone anywhere: it
 * lives on the home screen and in the footer, one tap from where it was.
 */
const NAV_ITEMS = [
  { href: "/app", label: "Home", icon: Home },
  { href: "/shop", label: "Shop", icon: Store },
  { href: "/reminders", label: "Reminders", icon: Bell },
  { href: "/ask-pharmacist", label: "Ask", icon: MessageCircle },
  { href: "/profile", label: "Profile", icon: User },
];

// DESIGN.md: visible 3px ring on every interactive element. This said 3px in
// the comment and shipped `ring-2` - so the nav, the most-tapped control in the
// product, had the only 2px ring in it. Matches `.pw-btn:focus-visible` and
// PageHeader now: 3px, same green, same alpha.
const FOCUS =
  "focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[rgba(52,217,138,0.5)] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0b0c09]";

function isActive(pathname: string, href: string): boolean {
  return pathname === href || (href !== "/app" && pathname.startsWith(href + "/"));
}

const MotionLink = motion.create(Link);

/** Press physics shared by both navs, matching TactileButton's spring. */
const NAV_SPRING = { type: "spring" as const, stiffness: 620, damping: 22, mass: 0.6 };
/** Slower and heavier than the press: the pill carries distance, not a tap. */
const PILL_SPRING = { type: "spring" as const, stiffness: 520, damping: 38, mass: 0.7 };

/**
 * The active-destination pill. `layoutId` is the whole point: framer-motion
 * matches the two instances across a route change, so the pill *travels* from
 * the old destination to the new one instead of vanishing and reappearing. That
 * movement is what tells you the nav is one object and you moved within it.
 * Under reduced-motion it simply appears, with no layout animation.
 */
function NavPill({ id, reduce }: { id: string; reduce: boolean | null }) {
  if (reduce) return <span className="absolute inset-0 rounded-full bg-emerald-500/12" />;
  return (
    <motion.span
      layoutId={id}
      className="absolute inset-0 rounded-full bg-emerald-500/12"
      transition={PILL_SPRING}
    />
  );
}

/** Live cart quantity; refreshes on navigation, tab focus, and cross-tab writes. */
function useCartCount(pathname: string): number {
  const [count, setCount] = useState(0);
  useEffect(() => {
    const read = (): void => {
      try {
        setCount(getCart().reduce((n, c) => n + (c.quantity || 0), 0));
      } catch {
        setCount(0);
      }
    };
    read();
    window.addEventListener("focus", read);
    window.addEventListener("storage", read);
    return () => {
      window.removeEventListener("focus", read);
      window.removeEventListener("storage", read);
    };
  }, [pathname]);
  return count;
}

function CartBadge({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <span className="absolute -right-1 -top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-emerald-500 px-1 text-[11px] font-bold leading-none text-black">
      {count > 99 ? "99+" : count}
    </span>
  );
}

/** Desktop top nav (hidden on mobile, where the bottom-nav takes over). */
function TopNav({ pathname, cartCount }: { pathname: string; cartCount: number }) {
  const reduce = useReducedMotion();
  return (
    <header className="sticky top-0 z-40 hidden border-b border-white/10 bg-[#0b0c09]/85 backdrop-blur-md md:block">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-center px-8">
        <nav aria-label="Primary" className="flex items-center gap-1">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = isActive(pathname, href);
            return (
              <MotionLink
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                whileTap={reduce ? undefined : { scale: 0.96 }}
                transition={NAV_SPRING}
                className={[
                  "relative inline-flex min-h-[40px] items-center gap-2 rounded-full px-3.5 text-[13px] font-semibold transition-colors",
                  active ? "text-emerald-400" : "text-white/55 hover:bg-white/5 hover:text-white",
                  FOCUS,
                ].join(" ")}
              >
                {/* Was a static `bg-emerald-500/12` on the active item, so the
                    highlight teleported between destinations. Same pill, now
                    carried by layoutId, so it travels. */}
                {active && <NavPill id="nav-pill-desktop" reduce={reduce} />}
                <Icon className="relative h-4 w-4" strokeWidth={active ? 2.4 : 2} />
                <span className="relative">{label}</span>
              </MotionLink>
            );
          })}
          <MotionLink
            href="/cart"
            aria-label={`Cart${cartCount > 0 ? `, ${cartCount} item${cartCount === 1 ? "" : "s"}` : ""}`}
            aria-current={isActive(pathname, "/cart") ? "page" : undefined}
            whileTap={reduce ? undefined : { scale: 0.96 }}
            transition={NAV_SPRING}
            className={[
              "relative ml-1 inline-flex h-11 w-11 items-center justify-center rounded-full transition-colors",
              isActive(pathname, "/cart")
                ? "bg-emerald-500/12 text-emerald-400"
                : "text-white/70 hover:bg-white/5 hover:text-white",
              FOCUS,
            ].join(" ")}
          >
            <ShoppingCart className="h-5 w-5" />
            <CartBadge count={cartCount} />
          </MotionLink>
        </nav>
      </div>
    </header>
  );
}

/**
 * Sticky back bar rendered by AppShell when `back` is set. Uses history when
 * available, falling back to `fallbackHref` for deep-linked entry so the button
 * never dead-ends. Sticky on mobile; sits in-flow below the desktop top nav.
 */
function BackBar({ title, fallbackHref = "/app" }: { title?: string; fallbackHref?: string }) {
  const router = useRouter();
  function goBack() {
    if (typeof window !== "undefined" && window.history.length > 1) router.back();
    else router.push(fallbackHref);
  }
  return (
    <div className="sticky top-0 z-30 flex items-center gap-3 border-b border-white/8 bg-[#0b0c09]/85 px-5 py-2.5 backdrop-blur-md md:static md:mx-auto md:w-full md:max-w-6xl md:bg-transparent md:px-8 md:py-4 md:backdrop-blur-none">
      <button
        onClick={goBack}
        aria-label="Go back"
        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/5 text-white/70 transition hover:border-white/20 hover:text-white active:bg-white/10 ${FOCUS}`}
      >
        <ArrowLeft className="h-4 w-4" />
      </button>
      {title && <p className="min-w-0 flex-1 truncate text-[15px] font-semibold text-white">{title}</p>}
    </div>
  );
}

/**
 * Mobile bottom nav (hidden on desktop). The most-tapped control in the product,
 * so it carries the system's press: this used to be `transition-colors` and
 * nothing else — a colour fade, which is the exact case DESIGN.md's
 * Press-Is-Physical Rule bans by name ("never a colour flash, never nothing").
 * On a phone there is no cursor, so press feedback IS the interaction.
 */
function BottomNav({ pathname, cartCount }: { pathname: string; cartCount: number }) {
  const reduce = useReducedMotion();
  const cartActive = isActive(pathname, "/cart");
  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-50 border-t border-white/10 bg-[#0e100c]/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-md md:hidden"
    >
      <div className="mx-auto flex max-w-md items-stretch justify-around">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = isActive(pathname, href);
          return (
            <MotionLink
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              whileTap={reduce ? undefined : { scale: 0.94 }}
              transition={NAV_SPRING}
              className={[
                "flex min-h-[56px] min-w-[56px] flex-1 flex-col items-center justify-center gap-1 py-2.5 text-[11px] font-semibold uppercase tracking-wide transition-colors",
                active ? "text-emerald-400" : "text-[#b1bdb0] hover:text-[#dcdddb]",
                FOCUS,
              ].join(" ")}
            >
              {/* The pill sits behind the icon, not the whole item: a full-height
                  fill on a 56px target reads as a selected row, not a
                  destination. */}
              <span className="relative inline-flex h-7 w-14 items-center justify-center">
                {active && <NavPill id="nav-pill-mobile" reduce={reduce} />}
                <Icon className="relative h-5 w-5" strokeWidth={active ? 2.4 : 2} />
              </span>
              {label}
            </MotionLink>
          );
        })}

        {/* Cart lives here too. It used to exist only in the desktop TopNav, so
            on a phone — the primary device for this product — there was no way
            to reach the cart from the nav at all. Both navs now offer the same
            destinations. */}
        <MotionLink
          href="/cart"
          aria-label={`Cart${cartCount > 0 ? `, ${cartCount} item${cartCount === 1 ? "" : "s"}` : ""}`}
          aria-current={cartActive ? "page" : undefined}
          whileTap={reduce ? undefined : { scale: 0.94 }}
          transition={NAV_SPRING}
          className={[
            "flex min-h-[56px] min-w-[56px] flex-1 flex-col items-center justify-center gap-1 py-2.5 text-[11px] font-semibold uppercase tracking-wide transition-colors",
            cartActive ? "text-emerald-400" : "text-[#b1bdb0] hover:text-[#dcdddb]",
            FOCUS,
          ].join(" ")}
        >
          <span className="relative inline-flex h-7 w-14 items-center justify-center">
            {cartActive && <NavPill id="nav-pill-mobile" reduce={reduce} />}
            <ShoppingCart className="relative h-5 w-5" strokeWidth={cartActive ? 2.4 : 2} />
            <CartBadge count={cartCount} />
          </span>
          Cart
        </MotionLink>
      </div>
    </nav>
  );
}

function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="border-t border-white/8 bg-[#0b0c09] px-6 pb-24 pt-10 text-sm text-white/45 md:px-8 md:pb-8">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 md:flex-row md:items-start md:justify-between">
        <div className="max-w-xs space-y-2">
          <span className="inline-flex rounded-lg bg-white px-2.5 py-1">
            <Image src={media.logo} alt="Peaceway Pharmacy" width={110} height={36} className="h-7 w-auto" />
          </span>
          <p className="leading-relaxed">{siteConfig.footerNote}</p>
          <p className="text-[#b1bdb0]">{siteConfig.address}</p>
        </div>
        {/* -my-2 keeps the row's visual rhythm while each link gets py-2, taking
            them from 20px tall to a real 36px target. They were pure text with no
            padding, on every route in the product. */}
        <nav
          aria-label="Footer"
          className="-my-2 flex flex-wrap items-center gap-x-6 gap-y-1 [&>*]:inline-flex [&>*]:min-h-[44px] [&>*]:items-center"
        >
          <Link href="/shop" className={`rounded transition-colors hover:text-white ${FOCUS}`}>Shop</Link>
          <Link href="/ask-pharmacist" className={`rounded transition-colors hover:text-white ${FOCUS}`}>Ask a Pharmacist</Link>
          <Link href="/requests" className={`rounded transition-colors hover:text-white ${FOCUS}`}>Requests</Link>
          <a
            href={siteConfig.telegramChannelUrl}
            target="_blank"
            rel="noreferrer noopener"
            className={`rounded transition-colors hover:text-white ${FOCUS}`}
          >
            Telegram
          </a>
          <a href={`mailto:${siteConfig.email}`} className={`rounded transition-colors hover:text-white ${FOCUS}`}>
            Contact
          </a>
        </nav>
      </div>
      <p className="mx-auto mt-8 max-w-6xl text-xs text-[#b1bdb0]">
        © {year} {siteConfig.name}. All rights reserved.
      </p>
    </footer>
  );
}

export function AppShell({
  children,
  back,
}: {
  children: React.ReactNode;
  back?: { title?: string; fallbackHref?: string } | boolean;
}) {
  const pathname = usePathname();
  const cartCount = useCartCount(pathname);
  const backProps = back === true ? {} : back || null;

  return (
    <div className="flex min-h-screen flex-col bg-[#0b0c09] pt-[env(safe-area-inset-top)]">
      <OfflineBanner />
      <TopNav pathname={pathname} cartCount={cartCount} />
      {backProps !== null && <BackBar {...backProps} />}
      <main className="flex-1">{children}</main>
      <Footer />
      <BottomNav pathname={pathname} cartCount={cartCount} />
    </div>
  );
}

export function AppHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="space-y-1.5 px-5 pt-10 pb-6">
      <p className="text-xs font-semibold uppercase tracking-widest text-emerald-400">
        Peaceway Online
      </p>
      <h1 className="text-2xl font-bold leading-tight text-white">{title}</h1>
      {subtitle && (
        <p className="text-sm leading-relaxed text-white/50">{subtitle}</p>
      )}
    </div>
  );
}
