"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  DownloadCloud,
  UserCheck,
  Inbox,
  SlidersHorizontal,
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
} from "lucide-react";
import { useI18n } from "@/context/i18n";

export interface NavItem {
  href: string;
  labelKey: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
  urgent?: boolean;
}

export interface AppSidebarProps {
  reviewQueueCount?: number;
  needsAttentionCount?: number;
  className?: string;
}

export const AppSidebar: React.FC<AppSidebarProps> = ({
  reviewQueueCount = 17,
  needsAttentionCount = 3,
  className = "",
}) => {
  const { t } = useI18n();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("sidebar_collapsed");
    if (saved !== null) {
      setCollapsed(saved === "true");
    }
  }, []);

  const toggleCollapse = () => {
    const nextState = !collapsed;
    setCollapsed(nextState);
    localStorage.setItem("sidebar_collapsed", String(nextState));
  };

  const navItems: NavItem[] = [
    {
      href: "/ingestion",
      labelKey: "nav.ingestion",
      icon: DownloadCloud,
    },
    {
      href: "/workspace",
      labelKey: "nav.workspace",
      icon: UserCheck,
      badge: reviewQueueCount,
    },
    {
      href: "/ledger",
      labelKey: "nav.ledger",
      icon: Inbox,
      badge: needsAttentionCount,
      urgent: needsAttentionCount > 0,
    },
    {
      href: "/calibration",
      labelKey: "nav.calibration",
      icon: SlidersHorizontal,
    },
  ];

  return (
    <aside
      className={`relative flex flex-col justify-between border-r border-border bg-white transition-all duration-300 ease-in-out shrink-0 select-none z-30 ${
        collapsed ? "w-16" : "w-64"
      } ${className}`}
    >
      {/* Top Brand Header */}
      <div>
        <div className="flex items-center justify-between h-16 px-4 border-b border-border">
          {!collapsed ? (
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white shrink-0 shadow-xs">
                <Sparkles className="w-4 h-4" />
              </div>
              <div className="flex flex-col min-w-0">
                <span className="font-bold text-sm tracking-tight text-foreground truncate">
                  {t("nav.brand_title")}
                </span>
                <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider truncate">
                  {t("nav.brand_subtitle")}
                </span>
              </div>
            </div>
          ) : (
            <div className="mx-auto w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white shrink-0 shadow-xs">
              <Sparkles className="w-4 h-4" />
            </div>
          )}
        </div>

        {/* Navigation Links */}
        <nav className="p-2 space-y-1 mt-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            const label = t(item.labelKey);

            return (
              <Link
                key={item.href}
                href={item.href}
                title={collapsed ? label : undefined}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors relative group ${
                  isActive
                    ? "bg-primary text-white shadow-xs"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                } ${collapsed ? "justify-center px-2" : ""}`}
              >
                <Icon className={`w-4 h-4 shrink-0 ${isActive ? "text-white" : ""}`} />

                {!collapsed && (
                  <span className="flex-1 truncate">{label}</span>
                )}

                {!collapsed && item.badge !== undefined && item.badge > 0 && (
                  <span
                    className={`text-[11px] font-semibold px-2 py-0.5 rounded-full shrink-0 ${
                      isActive
                        ? "bg-white/20 text-white"
                        : item.urgent
                        ? "bg-destructive text-white animate-pulse"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}

                {/* Collapsed Tooltip */}
                {collapsed && (
                  <div className="absolute left-full ml-2 px-2.5 py-1 bg-dark text-white text-xs rounded shadow-md whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50">
                    {label}
                    {item.badge !== undefined && item.badge > 0 && ` (${item.badge})`}
                  </div>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Controls: Collapse Toggle & Engine Status */}
      <div className="p-2 border-t border-border space-y-2">
        <button
          type="button"
          onClick={toggleCollapse}
          className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors ${
            collapsed ? "justify-center px-2" : ""
          }`}
          title={collapsed ? t("nav.expand") : t("nav.collapse")}
        >
          {collapsed ? (
            <PanelLeftOpen className="w-4 h-4" />
          ) : (
            <>
              <PanelLeftClose className="w-4 h-4" />
              <span>{t("nav.collapse")}</span>
            </>
          )}
        </button>

        {!collapsed && (
          <div className="px-3 py-1.5 rounded-md bg-muted/60 text-[11px] text-muted-foreground flex items-center justify-between">
            <span>SQLite WAL Mode</span>
            <span className="inline-block w-2 h-2 rounded-full bg-positive animate-pulse" />
          </div>
        )}
      </div>
    </aside>
  );
};
