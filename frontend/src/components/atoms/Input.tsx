"use client";

import React from "react";
import { LucideIcon, X } from "lucide-react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  icon?: LucideIcon;
  error?: string;
  onClear?: () => void;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ icon: Icon, error, onClear, value, className = "", ...props }, ref) => {
    return (
      <div className="w-full">
        <div className="relative flex items-center">
          {Icon && (
            <div className="absolute left-3 text-muted-foreground pointer-events-none">
              <Icon className="w-4 h-4" />
            </div>
          )}

          <input
            ref={ref}
            value={value}
            className={`w-full bg-white border rounded-lg text-sm text-foreground placeholder:text-muted-foreground transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent ${
              Icon ? "pl-9" : "pl-3"
            } ${onClear && value ? "pr-9" : "pr-3"} py-2 ${
              error ? "border-destructive focus:ring-destructive" : "border-border"
            } ${className}`}
            {...props}
          />

          {onClear && value && (
            <button
              type="button"
              onClick={onClear}
              className="absolute right-2.5 text-muted-foreground hover:text-foreground p-0.5 rounded transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {error && <p className="text-xs text-destructive mt-1">{error}</p>}
      </div>
    );
  }
);

Input.displayName = "Input";

