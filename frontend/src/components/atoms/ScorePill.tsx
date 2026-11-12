"use client";

import React from "react";
import { Sparkles, CheckCircle2, AlertTriangle, ShieldAlert, HelpCircle } from "lucide-react";

export interface ScorePillProps {
  score: number | null | undefined;
  showIcon?: boolean;
  size?: "sm" | "md";
  className?: string;
}

export const ScorePill: React.FC<ScorePillProps> = ({
  score,
  showIcon = true,
  size = "md",
  className = "",
}) => {
  const sizeClasses = size === "sm" ? "text-xs px-2 py-0.5" : "text-sm px-2.5 py-1";

  if (score === null || score === undefined) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-muted text-muted-foreground border border-border ${sizeClasses} ${className}`}
        title="Unscored"
      >
        {showIcon && <HelpCircle className="w-3.5 h-3.5" />}
        <span>-- / 4</span>
      </span>
    );
  }

  // Score 4: DeepTech / Exceptional Match
  if (score >= 4) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 font-semibold rounded-full bg-emerald-100 text-emerald-900 border border-emerald-300 ${sizeClasses} ${className}`}
        title="Score 4/4: Exceptional DeepTech Fit"
      >
        {showIcon && <Sparkles className="w-3.5 h-3.5 text-emerald-700" />}
        <span>4 / 4</span>
      </span>
    );
  }

  // Score 3: Strong Application Match
  if (score === 3) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 font-semibold rounded-full bg-blue-100 text-blue-900 border border-blue-300 ${sizeClasses} ${className}`}
        title="Score 3/4: Strong Application Fit"
      >
        {showIcon && <CheckCircle2 className="w-3.5 h-3.5 text-blue-700" />}
        <span>3 / 4</span>
      </span>
    );
  }

  // Score 2: Weak / Wrapper
  if (score === 2) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-amber-100 text-amber-900 border border-amber-300 ${sizeClasses} ${className}`}
        title="Score 2/4: Weak Fit / Chatbot Wrapper"
      >
        {showIcon && <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />}
        <span>2 / 4</span>
      </span>
    );
  }

  // Score 1: Noise / Adversarial Injection
  if (score === 1) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-red-100 text-red-900 border border-red-300 ${sizeClasses} ${className}`}
        title="Score 1/4: Noise / Adversarial Injection"
      >
        {showIcon && <ShieldAlert className="w-3.5 h-3.5 text-red-700" />}
        <span>1 / 4</span>
      </span>
    );
  }

  // Score 0: Sparse / Insufficient Evidence
  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-gray-100 text-gray-700 border border-gray-300 ${sizeClasses} ${className}`}
      title="Score 0/4: Sparse Profile / Insufficient Evidence"
    >
      {showIcon && <AlertTriangle className="w-3.5 h-3.5 text-gray-500" />}
      <span>0 / 4</span>
    </span>
  );
};
