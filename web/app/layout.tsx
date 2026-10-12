import type { Metadata } from "next";
import type { ReactNode } from "react";
import "@fontsource/source-sans-3/latin-400.css";
import "@fontsource/source-sans-3/latin-600.css";
import "@fontsource/source-sans-3/latin-700.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "HighGround",
  description: "Flood preparation and recovery for small shops.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
