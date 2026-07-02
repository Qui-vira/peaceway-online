"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ClipboardList,
  Home,
  MessageCircle,
  Search,
  User,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/app", label: "Home", icon: Home },
  { href: "/request", label: "Availability", icon: Search },
  { href: "/ask-pharmacist", label: "Ask", icon: MessageCircle },
  { href: "/requests", label: "Requests", icon: ClipboardList },
  { href: "/profile", label: "Profile", icon: User },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-[#0b0c09] pb-24">
      {children}

      <nav className="fixed bottom-0 inset-x-0 z-50 border-t border-white/10 bg-[#0e100c]/95 backdrop-blur-md">
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
