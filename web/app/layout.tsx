import type { Metadata } from "next";
import { DM_Sans, Syne } from "next/font/google";
import type { ReactNode } from "react";
import { MotionEffects } from "@/components/providers/motion-effects";
import { PwaRegister } from "@/components/providers/pwa-register";
import "@/app/globals.css";

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
  title: "Peaceway Online | Lagos Pharmacy - Order Medicine on Telegram",
  description:
    "Genuine medicines, pharmacist guidance, and delivery across Lagos. Order through Telegram from Peaceway Pharmacy, Igando.",
  openGraph: {
    title: "Peaceway Online | Lagos Pharmacy - Order Medicine on Telegram",
    description:
      "Genuine medicines, pharmacist guidance, and delivery across Lagos. Order through Telegram from Peaceway Pharmacy, Igando.",
    type: "website",
    url: "/",
    images: ["/images/pharmacy_photos-1782916474882.jpg"]
  },
  icons: {
    icon: "/icons/icon-192.png",
    apple: "/icons/icon-192.png"
  },
  alternates: {
    canonical: "/"
  }
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
        <meta name="theme-color" content="#0B0C09" />
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
