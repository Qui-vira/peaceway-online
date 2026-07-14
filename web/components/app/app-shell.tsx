"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ArrowLeft,
  Bell,
  ClipboardList,
  Home,
  MessageCircle,
  ShoppingCart,
  User,
} from "lucide-react";
import { getCart } from "@/lib/cart";
import { media } from "@/lib/media";
import { siteConfig } from "@/lib/constants";

const NAV_ITEMS = [
  { href: "/app", label: "Home", icon: Home },
  { href: "/reminders", label: "Reminders", icon: Bell },
  { href: "/ask-pharmacist", label: "Ask", icon: MessageCircle },
  { href: "/requests", label: "Requests", icon: ClipboardList },
  { href: "/profile", label: "Profile", icon: User },
];

// AA-safe focus ring (DESIGN.md: visible 3px ring on every interactive element).
const FOCUS =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/70 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0b0c09]";

function isActive(pathname: string, href: string): boolean {
  return pathname === href || (href !== "/app" && pathname.startsWith(href + "/"));
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
    <span className="absolute -right-1 -top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-emerald-500 px-1 text-[10px] font-bold leading-none text-black">
      {count > 99 ? "99+" : count}
    </span>
  );
}

/** Desktop top nav (hidden on mobile, where the bottom-nav takes over). */
function TopNav({ pathname, cartCount }: { pathname: string; cartCount: number }) {
  return (
    <header className="sticky top-0 z-40 hidden border-b border-white/10 bg-[#0b0c09]/85 backdrop-blur-md md:block">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-8">
        <Link href="/app" aria-label="Peaceway Online home" className={`rounded-lg ${FOCUS}`}>
          <span className="inline-flex rounded-lg bg-white px-2.5 py-1 shadow-[0_2px_12px_rgba(0,0,0,0.22)]">
            <Image src={media.logo} alt="Peaceway Pharmacy" width={110} height={36} className="h-8 w-auto" />
          </span>
        </Link>

        <nav aria-label="Primary" className="flex items-center gap-1">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = isActive(pathname, href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={[
                  "inline-flex min-h-[40px] items-center gap-2 rounded-full px-3.5 text-[13px] font-semibold transition-colors",
                  active
                    ? "bg-emerald-500/12 text-emerald-400"
                    : "text-white/55 hover:bg-white/5 hover:text-white",
                  FOCUS,
                ].join(" ")}
              >
                <Icon className="h-4 w-4" strokeWidth={active ? 2.4 : 2} />
                {label}
              </Link>
            );
          })}
          <Link
            href="/cart"
            aria-label={`Cart${cartCount > 0 ? `, ${cartCount} item${cartCount === 1 ? "" : "s"}` : ""}`}
            aria-current={isActive(pathname, "/cart") ? "page" : undefined}
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
          </Link>
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

/** Mobile bottom nav (hidden on desktop). */
function BottomNav({ pathname }: { pathname: string }) {
  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-50 border-t border-white/10 bg-[#0e100c]/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-md md:hidden"
    >
      <div className="mx-auto flex max-w-md items-stretch justify-around">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = isActive(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={[
                "flex min-h-[56px] min-w-[56px] flex-1 flex-col items-center justify-center gap-1 py-2.5 text-[10px] font-semibold uppercase tracking-wide transition-colors",
                active ? "text-emerald-400" : "text-white/40 hover:text-white/70",
                FOCUS,
              ].join(" ")}
            >
              <Icon className="h-5 w-5" strokeWidth={active ? 2.4 : 2} />
              {label}
            </Link>
          );
        })}
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
          <p className="text-white/35">{siteConfig.address}</p>
        </div>
        <nav aria-label="Footer" className="flex flex-wrap gap-x-6 gap-y-2">
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
      <p className="mx-auto mt-8 max-w-6xl text-xs text-white/30">
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
      <TopNav pathname={pathname} cartCount={cartCount} />
      {backProps !== null && <BackBar {...backProps} />}
      <main className="flex-1">{children}</main>
      <Footer />
      <BottomNav pathname={pathname} />
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
