"use client";

import React from "react";
import { LucideIcon } from "lucide-react";

export interface TabItem {
  key: string;
  label: string;
  icon?: LucideIcon;
  count?: number;
  urgent?: boolean;
}

export interface TabsProps {
  variant?: "line" | "pills";
  items: TabItem[];
  activeKey: string;
  onChange: (key: string) => void;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({
  variant = "line",
  items,
  activeKey,
  onChange,
  className = "",
}) => {
  if (variant === "pills") {
    return (
      <div className={`flex flex-wrap items-center gap-1.5 p-1 bg-muted/60 rounded-xl border border-border/80 ${className}`}>
        {items.map((tab) => {
          const isActive = tab.key === activeKey;
          const Icon = tab.icon;

          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => onChange(tab.key)}
              className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all select-none ${
                isActive
                  ? "bg-primary text-white shadow-xs"
                  : "text-muted-foreground hover:text-foreground hover:bg-white/80"
              }`}
            >
              {Icon && <Icon className="w-3.5 h-3.5 shrink-0" />}
              <span>{tab.label}</span>

              {tab.count !== undefined && (
                <span
                  className={`text-[11px] px-1.5 py-0.2 rounded-full font-semibold ${
                    isActive
                      ? "bg-white/20 text-white"
                      : tab.urgent
                      ? "bg-destructive text-white animate-pulse"
                      : "bg-black/5 text-muted-foreground"
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>
    );
  }

  // Line Tabs (Underlined)
  return (
    <div className={`flex items-center gap-6 border-b border-border ${className}`}>
      {items.map((tab) => {
        const isActive = tab.key === activeKey;
        const Icon = tab.icon;

        return (
          <button
            key={tab.key}
            type="button"
            onClick={() => onChange(tab.key)}
            className={`relative flex items-center gap-2 py-3 text-sm font-medium transition-colors select-none ${
              isActive
                ? "text-primary font-semibold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {Icon && <Icon className="w-4 h-4 shrink-0" />}
            <span>{tab.label}</span>

            {tab.count !== undefined && (
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                  isActive
                    ? "bg-primary-light text-primary"
                    : tab.urgent
                    ? "bg-destructive text-white animate-pulse"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {tab.count}
              </span>
            )}

            {isActive && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-t-full" />
            )}
          </button>
        );
      })}
    </div>
  );
};

