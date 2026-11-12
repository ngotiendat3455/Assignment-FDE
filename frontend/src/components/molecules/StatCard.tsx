"use client";

import React from "react";
import { LucideIcon } from "lucide-react";
import { useI18n } from "@/context/i18n";

export interface StatCardProps {
  icon: LucideIcon;
  label: string;
  value: string | number;
  subtext?: string;
  variant?: "default" | "urgent" | "positive" | "primary";
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  icon: Icon,
  label,
  value,
  subtext,
  variant = "default",
  className = "",
}) => {
  const { t } = useI18n();
  const isUrgent = variant === "urgent";

  const variantStyles = {
    default: "bg-white border-border text-foreground",
    urgent: "bg-red-50/60 border-destructive shadow-xs ring-1 ring-destructive/30",
    positive: "bg-green-50/50 border-positive/30 text-foreground",
    primary: "bg-primary/5 border-primary/30 text-foreground",
  };

  const iconColors = {
    default: "text-muted-foreground bg-muted",
    urgent: "text-destructive bg-red-100 animate-pulse",
    positive: "text-positive bg-green-100",
    primary: "text-primary bg-primary-light",
  };

  return (
    <div
      className={`p-4 rounded-xl border transition-all flex flex-col justify-between ${
        variantStyles[variant]
      } ${className}`}
    >
      <div className="flex items-center justify-between gap-3 mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        <div className={`p-2 rounded-lg ${iconColors[variant]}`}>
          <Icon className="w-4 h-4 shrink-0" />
        </div>
      </div>

      <div>
        <div className="flex items-baseline gap-2">
          <span
            className={`text-2xl font-bold tracking-tight ${
              isUrgent ? "text-destructive" : "text-foreground"
            }`}
          >
            {value}
          </span>
          {isUrgent && (
            <span className="text-[10px] font-bold text-white bg-destructive px-1.5 py-0.5 rounded uppercase tracking-wider animate-pulse">
              {t("status.urgent_tag")}
            </span>
          )}
        </div>

        {subtext && (
          <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
            {subtext}
          </p>
        )}
      </div>
    </div>
  );
};
