// name: app/layout.tsx
// purpose: Root layout for the whole CloudDesk frontend: fonts, global styles, and the shared
//          TooltipProvider/Toaster wrappers both the customer portal and the support console need.
//          2026-09-25 redesign: swapped Geist Sans for Inter as the primary UI typeface (spec
//          section 14 — moving off the previous serif-leaning look toward a modern SaaS sans-serif
//          hierarchy); Geist Mono is kept for the technical/monospace bits (API keys, transaction
//          references, thread ids) since it reinforces the "technical, trustworthy" tone.
// author: CloudDesk Team
// date: 2026-09-25

import type { Metadata } from "next";
import { Geist_Mono, Inter } from "next/font/google";

import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

import "./globals.css";

const inter = Inter({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CloudDesk",
  description: "CloudDesk — AI-powered customer support platform",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <TooltipProvider>{children}</TooltipProvider>
        <Toaster richColors closeButton position="top-right" />
      </body>
    </html>
  );
}
