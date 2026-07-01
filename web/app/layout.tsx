import type { Metadata } from "next";
import type { Viewport } from "next";
import { DM_Sans, Syne } from "next/font/google";
import type { ReactNode } from "react";
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
  metadataBase: new URL("https://peacewayonline.com.ng"),
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
      </head>
      <body>
        <PwaRegister />
        <MotionEffects />
        {children}
      </body>
    </html>
  );
}
