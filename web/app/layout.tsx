import type { Metadata } from "next";
import type { Viewport } from "next";
import { DM_Sans, Syne } from "next/font/google";
import type { ReactNode } from "react";
import { AppLoader, LOADER_SCOPE } from "@/components/brand/app-loader";
import { MotionEffects } from "@/components/providers/motion-effects";
import { PwaRegister } from "@/components/providers/pwa-register";
import "@/app/globals.css";
import { siteConfig } from "@/lib/constants";

const syne = Syne({
  subsets: ["latin"],
  weight: ["700", "800"],
  variable: "--font-syne",
  display: "swap"
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-dm-sans",
  display: "swap"
});

export const metadata: Metadata = {
  // Single source of truth in lib/constants.ts, so this cannot drift from the
  // sitemap and robots.txt again.
  metadataBase: new URL(siteConfig.url),
  title: siteConfig.title,
  description: siteConfig.description,
  openGraph: {
    title: siteConfig.title,
    description: siteConfig.description,
    type: "website",
    url: "/",
    images: ["/images/pharmacy_photos-1782916474882.jpg"]
  },
  icons: {
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" }
    ],
    apple: "/icons/icon-192.png"
  },
  alternates: {
    canonical: "/"
  }
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#0F673C"
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps): JSX.Element {
  return (
    <html lang="en" className={`${syne.variable} ${dmSans.variable}`}>
      <head>
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
        {/* Loader assets. The poster doubles as the video's own poster frame and
            as the never-blank fallback; the cut-out is what travels at the end.
            Both are preloaded because they are needed in the first two seconds.
            The video itself uses preload="auto" on the element rather than
            <link rel="preload" as="video">, which browsers support unevenly. */}
        <link
          rel="preload"
          as="image"
          href="/branding/loader/peaceway-loader-poster.webp"
          type="image/webp"
        />
        <link
          rel="preload"
          as="image"
          href="/branding/loader/peaceway-loader-mark.webp"
          type="image/webp"
        />
        {/* Runs before first paint, before React, deliberately blocking, and
            ONLY when the scope actually gates replays. The loader is
            server-rendered so it covers the first frame, which means a visitor
            who should skip it would otherwise see a flash before hydration
            could remove it. Imported constant rather than a duplicated string,
            so the script and the component cannot drift apart. */}
        {LOADER_SCOPE === "first-visit-per-session" ? (
          <script
            dangerouslySetInnerHTML={{
              __html:
                "try{if(sessionStorage.getItem('pw-loader-seen')==='1')" +
                "document.documentElement.classList.add('pw-loader-skip')}catch(e){}",
            }}
          />
        ) : null}
      </head>
      <body>
        <PwaRegister />
        <MotionEffects />
        {/* App-open loader. Lives in the layout, not the template: a layout
            persists across client-side navigation, so this mounts once per real
            page load rather than re-firing on every route change. Client-only
            and purely additive - if its bundle never arrives, the app simply
            renders without it, and the page behind has already painted. */}
        <AppLoader />
        {children}
      </body>
    </html>
  );
}
