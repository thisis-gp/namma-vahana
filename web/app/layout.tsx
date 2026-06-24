import type { Metadata } from "next";
import { Archivo, IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import BackendWarmup from "@/components/BackendWarmup";
import "./globals.css";
import { BRAND } from "@/lib/brand";

async function kickBackendWake() {
  const origin = process.env.API_URL;
  if (!origin) return;
  try {
    await Promise.race([
      fetch(`${origin}/api/health`, { cache: "no-store" }),
      new Promise((resolve) => setTimeout(resolve, 2500)),
    ]);
  } catch {
    /* cold start — client overlay retries */
  }
}

// Display — a wide, confident grotesque with signage character.
const archivo = Archivo({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

// Body — institutional, highly legible.
const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

// Data — every number, plate, timestamp, H3 code. License-plate feel.
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: `${BRAND.name} — ${BRAND.tagline}`,
  description: BRAND.description,
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  // Fire-and-forget — don't block SSR or wake Render before the client splash shows.
  void kickBackendWake();

  return (
    <html
      lang="en"
      className={`${archivo.variable} ${plexSans.variable} ${plexMono.variable} h-full antialiased`}
    >
      <body className="min-h-full">
        <BackendWarmup>{children}</BackendWarmup>
      </body>
    </html>
  );
}
