import Link from "next/link";
import { siteConfig } from "@/lib/constants";

export default function OfflinePage(): JSX.Element {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: "40px 20px",
        background: "#0B0C09",
        color: "#DCDDDB"
      }}
    >
      <section
        style={{
          width: "100%",
          maxWidth: 560,
          border: "1px solid rgba(255,255,255,.08)",
          borderRadius: 24,
          padding: 28,
          background: "rgba(255,255,255,.03)",
          boxShadow: "0 20px 80px rgba(0,0,0,.35)"
        }}
      >
        <p style={{ fontSize: 12, letterSpacing: "0.18em", textTransform: "uppercase", color: "#A80B16", marginBottom: 12 }}>
          Offline mode
        </p>
        <h1 style={{ fontFamily: "var(--font-syne), sans-serif", fontSize: "clamp(28px, 6vw, 44px)", lineHeight: 1.05, marginBottom: 12 }}>
          Peaceway Online is temporarily offline.
        </h1>
        <p style={{ fontSize: 15, lineHeight: 1.75, color: "#B1BDB0", marginBottom: 24 }}>
          You can reopen the site when you are back online. The main pharmacy homepage and installable app shell are cached for quicker return visits.
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
          <Link
            href="/"
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: 44,
              padding: "0 22px",
              borderRadius: 999,
              background: "#0F673C",
              color: "#fff",
              fontSize: 14,
              fontWeight: 600,
              textDecoration: "none"
            }}
          >
            Try again
          </Link>
          <a
            href={siteConfig.telegramBotUrl}
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: 44,
              padding: "0 22px",
              borderRadius: 999,
              border: "1px solid rgba(220,221,219,.28)",
              color: "#DCDDDB",
              fontSize: 14,
              fontWeight: 600,
              textDecoration: "none"
            }}
          >
            Open Telegram
          </a>
        </div>
      </section>
    </main>
  );
}
