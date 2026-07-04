"use client";

import { useEffect, useRef, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import type { ApiError } from "@/lib/api";
import {
  linkTelegram,
  type CustomerProfile,
  type TelegramAuthPayload,
} from "@/lib/api/customers";
import { siteConfig } from "@/lib/constants";

declare global {
  interface Window {
    onTelegramAuth?: (user: TelegramAuthPayload) => void;
  }
}

const BOT_USERNAME = siteConfig.telegramBotUrl.split("/").pop() ?? "";

/**
 * "Connect Telegram" card for the /app dashboard. Renders the official
 * Telegram Login Widget; on auth, posts the signed payload to the backend
 * which verifies the signature before linking.
 */
export function ConnectTelegramCard({
  profile,
  onLinked,
}: {
  profile: CustomerProfile;
  onLinked: (profile: CustomerProfile) => void;
}) {
  const holder = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const linked = profile.telegram_linked === true;

  useEffect(() => {
    if (linked) return;
    const el = holder.current;
    if (!el) return;

    window.onTelegramAuth = async (user) => {
      setBusy(true);
      setError(null);
      try {
        onLinked(await linkTelegram(user));
      } catch (e) {
        setError(
          (e as ApiError)?.detail ?? "Could not connect Telegram. Try again."
        );
      } finally {
        setBusy(false);
      }
    };

    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.async = true;
    script.setAttribute("data-telegram-login", BOT_USERNAME);
    script.setAttribute("data-size", "medium");
    script.setAttribute("data-radius", "12");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    script.setAttribute("data-request-access", "write");
    el.appendChild(script);

    return () => {
      window.onTelegramAuth = undefined;
      el.replaceChildren();
    };
  }, [linked, onLinked]);

  if (linked) {
    return (
      <div className="flex items-center gap-4 rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.04] px-5 py-4">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-500/12">
          <CheckCircle2 className="h-5 w-5 text-emerald-400" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold text-white/85">
            Telegram connected
          </span>
          <span className="block text-xs text-white/45">
            {profile.telegram_username
              ? `@${profile.telegram_username} — order updates & reminders in your chat`
              : "Order updates & reminders now reach your Telegram chat"}
          </span>
        </span>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-white/6 bg-white/[0.025] px-5 py-4">
      <p className="text-sm font-semibold text-white/85">Connect Telegram</p>
      <p className="mt-0.5 text-xs text-white/45">
        Get order updates, request updates and pharmacist replies in your
        Telegram chat.
      </p>
      <div ref={holder} className="mt-3 min-h-[40px]" />
      {busy && <p className="mt-2 text-xs text-white/45">Connecting…</p>}
      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
    </div>
  );
}
