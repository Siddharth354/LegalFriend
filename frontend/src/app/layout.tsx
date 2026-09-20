import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "Nyaya-Dost",
  description: "A voice-first legal first-responder.",
  manifest: "/manifest.json",
  other: { notranslate: "notranslate" },
};

export const viewport: Viewport = {
  themeColor: "#000000",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>): ReactNode {
  return (
    <html lang="en" translate="no">
      <body>{children}</body>
    </html>
  );
}
