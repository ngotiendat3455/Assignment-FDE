"use client";

import React from "react";
import { Sparkles, Quote, Info } from "lucide-react";
import { EvidenceMark } from "../atoms/EvidenceMark";
import { useI18n } from "@/context/i18n";

export interface EvidenceCalloutProps {
  fitReason?: string | null;
  evidenceSnippet?: string | null;
  recentTweets?: string | null;
  className?: string;
}

export const EvidenceCallout: React.FC<EvidenceCalloutProps> = ({
  fitReason,
  evidenceSnippet,
  recentTweets,
  className = "",
}) => {
  const { t } = useI18n();

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Fit Reason Box */}
      {fitReason && (
        <div className="p-3.5 rounded-xl bg-blue-50/70 border border-blue-200/80 text-xs">
          <div className="flex items-center gap-1.5 font-semibold text-blue-900 mb-1">
            <Sparkles className="w-3.5 h-3.5 text-blue-700 shrink-0" />
            <span>{t("evidence.why_fit")}</span>
          </div>
          <p className="text-blue-950 leading-relaxed font-normal">{fitReason}</p>
        </div>
      )}

      {/* Verbatim Evidence Box */}
      {evidenceSnippet && (
        <div className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-300 text-xs">
          <div className="flex items-center gap-1.5 font-semibold text-amber-900 mb-1">
            <Quote className="w-3.5 h-3.5 text-amber-700 shrink-0" />
            <span>{t("evidence.verbatim")}</span>
          </div>
          <blockquote className="italic text-amber-950 font-medium pl-2 border-l-2 border-amber-400 my-1">
            &ldquo;{evidenceSnippet}&rdquo;
          </blockquote>
        </div>
      )}

      {/* Raw Tweet Content with Highlight */}
      {recentTweets && (
        <div className="p-3 rounded-lg bg-muted/60 border border-border text-xs text-muted-foreground">
          <div className="flex items-center gap-1 font-semibold text-foreground mb-1 text-[11px] uppercase tracking-wider">
            <Info className="w-3 h-3 text-muted-foreground" />
            <span>{t("evidence.recent_tweets")}</span>
          </div>
          <p className="leading-relaxed whitespace-pre-wrap break-words">
            <EvidenceMark text={recentTweets} snippet={evidenceSnippet} />
          </p>
        </div>
      )}
    </div>
  );
};
