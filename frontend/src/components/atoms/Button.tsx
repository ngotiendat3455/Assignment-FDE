"use client";

import React from "react";
import { LucideIcon, Loader2 } from "lucide-react";

export type ButtonVariant = "primary" | "secondary" | "destructive" | "positive" | "outline" | "ghost";
export type ButtonSize = "sm" | "md" | "lg" | "icon";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: LucideIcon;
  iconPosition?: "left" | "right";
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = "primary",
      size = "md",
      icon: Icon,
      iconPosition = "left",
      loading = false,
      disabled,
      className = "",
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed select-none";

    const variantStyles: Record<ButtonVariant, string> = {
      primary:
        "bg-primary text-white hover:bg-primary-hover focus:ring-primary shadow-xs active:translate-y-px",
      secondary:
        "bg-secondary text-white hover:opacity-90 focus:ring-secondary shadow-xs",
      destructive:
        "bg-destructive text-white hover:bg-destructive/90 focus:ring-destructive shadow-xs",
      positive:
        "bg-positive text-white hover:bg-positive/90 focus:ring-positive shadow-xs",
      outline:
        "border border-border bg-white text-foreground hover:bg-muted focus:ring-primary",
      ghost:
        "text-muted-foreground hover:text-foreground hover:bg-muted focus:ring-primary",
    };

    const sizeStyles: Record<ButtonSize, string> = {
      sm: "text-xs px-2.5 py-1.5 gap-1.5",
      md: "text-sm px-4 py-2 gap-2",
      lg: "text-base px-5 py-2.5 gap-2.5",
      icon: "p-2 aspect-square",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
        {...props}
      >
        {loading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : Icon && iconPosition === "left" ? (
          <Icon className="w-4 h-4 shrink-0" />
        ) : null}

        {children}

        {!loading && Icon && iconPosition === "right" ? (
          <Icon className="w-4 h-4 shrink-0" />
        ) : null}
      </button>
    );
  }
);

Button.displayName = "Button";

