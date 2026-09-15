import type { Metadata } from "next";
import Link from "next/link";
import { ClerkProvider } from "@clerk/nextjs";
import AppHeader from "@/components/AppHeader";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cost-Aware AI Router",
  description: "Production-style Gemini/Mistral router dashboard",
};

const navItems = [
  ["/", "Dashboard"],
  ["/router", "AI Router"],
  ["/connectors", "MCP Connectors"],
  ["/analytics", "Analytics"],
  ["/evaluation", "Evaluation"],
  ["/traces", "LangSmith / Traces"],
  ["/logs", "Logs"],
  ["/settings", "Settings"],
] as const;

const hasClerkKey = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY.trim());

import Sidebar from "@/components/Sidebar";

function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="content">{children}</main>
    </div>
  );
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const bodyContent = hasClerkKey ? (
    <ClerkProvider publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY!}>
      <AppShell>{children}</AppShell>
    </ClerkProvider>
  ) : (
    <AppShell>{children}</AppShell>
  );

  return (
    <html lang="en" className="dark h-full">
      <body className="min-h-full bg-[#070712] text-slate-100 antialiased">{bodyContent}</body>
    </html>
  );
}
