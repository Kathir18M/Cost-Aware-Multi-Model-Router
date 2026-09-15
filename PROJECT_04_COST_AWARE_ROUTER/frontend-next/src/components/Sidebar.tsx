"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useUser, UserButton, SignInButton } from "@clerk/nextjs";
import { getDashboard } from "@/lib/api";
import { formatCost } from "@/lib/format";

const navItems = [
  { href: "/", label: "Dashboard", icon: "⊞" },
  { href: "/router", label: "Console", icon: "❯" },
  { href: "/history", label: "History", icon: "🕒" },
  { href: "/models", label: "Models", icon: "⚙" },
  { href: "/analytics", label: "Analytics", icon: "📊" },
  { href: "/connectors", label: "Connectors", icon: "❮" },
] as const;

export default function Sidebar() {
  const pathname = usePathname();
  const { user, isLoaded } = useUser();
  const [savings, setSavings] = useState<number>(0.00336);

  useEffect(() => {
    getDashboard()
      .then((data) => {
        if (data && typeof data.total_savings === "number" && data.total_savings > 0) {
          setSavings(data.total_savings);
        }
      })
      .catch(() => {});
  }, []);

  return (
    <aside className="sidebar flex flex-col justify-between h-full bg-[#0a0d14] border-r border-slate-800/80 p-5 text-slate-200 min-h-screen">
      <div>
        {/* Logo / Title Header */}
        <div className="flex items-center gap-2 mb-8">
          <div className="w-6 h-6 rounded bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400 font-bold text-xs">
            ⚡
          </div>
          <span className="font-bold text-lg tracking-tight text-white">Cost-Aware AI Router</span>
        </div>

        {/* Navigation Menu */}
        <nav className="space-y-1.5">
          {navItems.map((item) => {
            const isActive = pathname === item.href || (item.href !== "/" && pathname?.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm transition-all duration-150 ${
                  isActive
                    ? "bg-[#181d2a] text-amber-400 font-semibold border border-amber-500/30 shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
                }`}
              >
                <span className={isActive ? "text-amber-400" : "text-slate-500"}>
                  {isActive && item.href === "/router" ? ">" : item.icon}
                </span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Bottom Footer Section: Monthly Savings & User Badge */}
      <div className="pt-6 border-t border-slate-800/60 space-y-4">
        {/* Saved this month widget */}
        <div>
          <div className="text-[11px] uppercase tracking-wider text-slate-500 font-medium mb-1">
            Saved this month
          </div>
          <div className="text-xl font-bold text-amber-400 tracking-tight">
            ${savings.toFixed(5)}
          </div>
        </div>

        {/* User Auth Badge */}
        <div className="flex items-center gap-2.5 pt-2">
          {isLoaded && user ? (
            <div className="flex items-center gap-3 w-full">
              <UserButton />
              <div className="flex flex-col min-w-0 text-xs">
                <span className="text-slate-200 font-medium truncate">
                  {user.firstName || user.emailAddresses[0]?.emailAddress?.split("@")[0] || "User"}
                </span>
                <span className="text-slate-500 text-[11px]">Signed in</span>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <SignInButton mode="modal">
                <button type="button" className="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium border border-slate-700 transition">
                  Sign In
                </button>
              </SignInButton>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
