// name: app/layout.tsx
// purpose: Root layout for the whole CloudDesk frontend: fonts, global styles, and the shared
//          TooltipProvider/Toaster wrappers both the customer portal and the support console need.
// author: CloudDesk Team
// date: 2026-09-24

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

import "./globals.css";

const geistSans = Geist({
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
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <TooltipProvider>{children}</TooltipProvider>
        <Toaster richColors closeButton position="top-right" />
      </body>
    </html>
  );
}
