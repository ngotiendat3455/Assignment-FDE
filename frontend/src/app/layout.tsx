import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AppProviders } from "@/components/providers/AppProviders";
import type { RuntimeConfig } from "@/context/runtime";

export const dynamic = "force-dynamic";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "X-Scout AI – Autonomous Scouting & Outreach System",
  description: "AI-powered scout and personalized outreach tool for frontier tech builders in Southeast Asia.",
};

async function resolveServerRuntimeConfig(): Promise<RuntimeConfig> {
  const envProfile = (process.env.RUNTIME_PROFILE || "").trim().toUpperCase();
  const envDispatch = (process.env.DISPATCH_MODE || "").trim().toUpperCase();

  if (envProfile) {
    return {
      runtimeProfile: envProfile,
      dispatchMode: envDispatch || (envProfile === "LIVE_PRODUCTION" ? "LIVE_X" : "SANDBOX"),
    };
  }

  // Fallback for local dev when frontend runs outside Docker without RUNTIME_PROFILE in frontend/.env
  try {
    const internalBase = (
      process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000/api"
    ).replace(/\/+$/, "");
    const res = await fetch(`${internalBase}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(1500),
    });
    if (res.ok) {
      const data = (await res.json()) as {
        runtime_profile?: string;
        dispatch_mode?: string;
      };
      return {
        runtimeProfile: (data.runtime_profile || "OFFLINE_MOCK").toUpperCase(),
        dispatchMode: (data.dispatch_mode || "SANDBOX").toUpperCase(),
      };
    }
  } catch {
    // Ignore if backend is offline during static build/startup
  }

  return {
    runtimeProfile: "OFFLINE_MOCK",
    dispatchMode: envDispatch || "SANDBOX",
  };
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const initialRuntime = await resolveServerRuntimeConfig();

  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <AppProviders initialRuntime={initialRuntime}>{children}</AppProviders>
      </body>
    </html>
  );
}
