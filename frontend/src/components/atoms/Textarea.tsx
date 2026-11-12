"use client";

import React from "react";
import { useI18n } from "@/context/i18n";

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: string;
  maxCharacters?: number;
  showCounter?: boolean;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      error,
      maxCharacters = 500,
      showCounter = true,
      value = "",
      className = "",
      ...props
    },
    ref
  ) => {
    const { t } = useI18n();
    const stringVal = String(value || "");
    const currentLength = stringVal.length;
    const isOverLimit = currentLength > maxCharacters;

    return (
      <div className="w-full">
        <textarea
          ref={ref}
          value={value}
          className={`w-full bg-white border rounded-lg text-sm text-foreground placeholder:text-muted-foreground p-3 transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-y min-h-[100px] ${
            isOverLimit || error
              ? "border-destructive focus:ring-destructive"
              : "border-border"
          } ${className}`}
          {...props}
        />

        <div className="flex items-center justify-between text-xs mt-1.5 px-0.5">
          {error ? (
            <span className="text-destructive font-medium">{error}</span>
          ) : (
            <span
              className={
                isOverLimit
                  ? "text-destructive font-semibold animate-pulse"
                  : "text-muted-foreground"
              }
            >
              {isOverLimit
                ? t("composer.exceeded")
                : t("composer.optimal")}
            </span>
          )}

          {showCounter && (
            <span
              className={`font-mono font-medium ${
                isOverLimit ? "text-destructive font-bold" : "text-muted-foreground"
              }`}
            >
              {currentLength} / {maxCharacters}
            </span>
          )}
        </div>
      </div>
    );
  }
);

Textarea.displayName = "Textarea";
