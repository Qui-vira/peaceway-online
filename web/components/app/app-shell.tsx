"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Bell,
  ClipboardList,
  Home,
  MessageCircle,
  User,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/app", label: "Home", icon: Home },
  { href: "/reminders", label: "Reminders", icon: Bell },
  { href: "/ask-pharmacist", label: "Ask", icon: MessageCircle },
  { href: "/requests", label: "Requests", icon: ClipboardList },
  { href: "/profile", label: "Profile", icon: User },
];

/**
 * Sticky back bar rendered by AppShell when `back` is set. Uses history when
 * available, falling back to `fallbackHref` for deep-linked entry so the button
 * never dead-ends.
 */
function BackBar({ title, fallbackHref = "/app" }: { title?: string; fallbackHref?: string }) {
  const router = useRouter();
  function goBack() {
    if (typeof window !== "undefined" && window.history.length > 1) router.back();
    else router.push(fallbackHref);
  }
  return (
    <div className="sticky top-0 z-40 flex items-center gap-3 border-b border-white/8 bg-[#0b0c09]/85 px-5 py-3 backdrop-blur-md">
      <button
        onClick={goBack}
        aria-label="Go back"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/5 text-white/70 transition hover:border-white/20 hover:text-white active:bg-white/10"
      >
        <ArrowLeft className="h-4 w-4" />
      </button>
      {title && <p className="min-w-0 flex-1 truncate text-[15px] font-semibold text-white">{title}</p>}
    </div>
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
  const backProps = back === true ? {} : back || null;

  return (
    <div className="min-h-screen bg-[#0b0c09] pb-28 pt-[env(safe-area-inset-top)]">
      {backProps !== null && <BackBar {...backProps} />}
      {children}

      <nav className="fixed bottom-0 inset-x-0 z-50 border-t border-white/10 bg-[#0e100c]/95 backdrop-blur-md pb-[env(safe-area-inset-bottom)]">
        <div className="mx-auto flex max-w-md items-stretch justify-around">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active =
              pathname === href || (href !== "/app" && pathname.startsWith(href + "/"));
            return (
              <Link
                key={href}
                href={href}
                className={[
                  "flex min-w-[56px] flex-1 flex-col items-center gap-1 py-3 text-[10px] font-semibold uppercase tracking-wide transition-colors",
                  active ? "text-emerald-400" : "text-white/40 hover:text-white/70",
                ].join(" ")}
              >
                <Icon className="h-5 w-5" strokeWidth={active ? 2.4 : 2} />
                {label}
              </Link>
            );
          })}
        </div>
      </nav>
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
