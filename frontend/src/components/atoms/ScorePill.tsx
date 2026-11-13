"use client";

import React from "react";
import { Sparkles, CheckCircle2, AlertTriangle, ShieldAlert, HelpCircle } from "lucide-react";

export interface ScorePillProps {
  score: number | null | undefined;
  showIcon?: boolean;
  size?: "sm" | "md";
  className?: string;
}

type ScoreBadgeConfig = {
  label: string;
  title: string;
  pillClasses: string;
  iconColor: string;
  Icon: React.ComponentType<{ className?: string }>;
};

function getScoreConfig(score: number | null | undefined): ScoreBadgeConfig {
  if (score === null || score === undefined) {
    return {
      label: "-- / 4",
      title: "Unscored",
      pillClasses: "font-medium bg-muted text-muted-foreground border-border",
      iconColor: "",
      Icon: HelpCircle,
    };
  }
  if (score >= 4) {
    return {
      label: "4 / 4",
      title: "Score 4/4: Exceptional DeepTech Fit",
      pillClasses: "font-semibold bg-emerald-100 text-emerald-900 border-emerald-300",
      iconColor: "text-emerald-700",
      Icon: Sparkles,
    };
  }
  if (score === 3) {
    return {
      label: "3 / 4",
      title: "Score 3/4: Strong Application Fit",
      pillClasses: "font-semibold bg-blue-100 text-blue-900 border-blue-300",
      iconColor: "text-blue-700",
      Icon: CheckCircle2,
    };
  }
  if (score === 2) {
    return {
      label: "2 / 4",
      title: "Score 2/4: Weak Fit / Chatbot Wrapper",
      pillClasses: "font-medium bg-amber-100 text-amber-900 border-amber-300",
      iconColor: "text-amber-700",
      Icon: AlertTriangle,
    };
  }
  if (score === 1) {
    return {
      label: "1 / 4",
      title: "Score 1/4: Noise / Adversarial Injection",
      pillClasses: "font-medium bg-red-100 text-red-900 border-red-300",
      iconColor: "text-red-700",
      Icon: ShieldAlert,
    };
  }
  return {
    label: "0 / 4",
    title: "Score 0/4: Sparse Profile / Insufficient Evidence",
    pillClasses: "font-medium bg-gray-100 text-gray-700 border-gray-300",
    iconColor: "text-gray-500",
    Icon: AlertTriangle,
  };
}

/** Displays a single-line AI fit score badge (0/4 to 4/4 or unscored). */
export const ScorePill: React.FC<ScorePillProps> = ({
  score,
  showIcon = true,
  size = "md",
  className = "",
}) => {
  const sizeClasses = size === "sm" ? "text-xs px-2 py-0.5" : "text-sm px-2.5 py-1";
  const { label, title, pillClasses, iconColor, Icon } = getScoreConfig(score);

  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap shrink-0 rounded-full border ${pillClasses} ${sizeClasses} ${className}`}
      title={title}
    >
      {showIcon && <Icon className={`w-3.5 h-3.5 shrink-0 ${iconColor}`} />}
      <span>{label}</span>
    </span>
  );
};
