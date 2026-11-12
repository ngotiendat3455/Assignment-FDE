"use client";

import React from "react";
import { LucideIcon } from "lucide-react";

export type BadgeVariant =
  | "primary"
  | "positive"
  | "warning"
  | "destructive"
  | "urgent"
  | "muted"
  | "outline";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: "sm" | "md";
  icon?: LucideIcon;
  pulse?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "primary",
  size = "md",
  icon: Icon,
  pulse = false,
  className = "",
  ...props
}) => {
  const baseStyles =
    "inline-flex items-center font-medium rounded-full select-none shrink-0";

  const sizeStyles = {
    sm: "text-[11px] px-2 py-0.5 gap-1",
    md: "text-xs px-2.5 py-1 gap-1.5",
  };

  const variantStyles: Record<BadgeVariant, string> = {
    primary:
      "bg-primary-light text-primary border border-primary/20",
    positive:
      "bg-green-50 text-positive border border-positive/20",
    warning:
      "bg-amber-50 text-amber-800 border border-amber-200",
    destructive:
      "bg-red-50 text-destructive border border-destructive/20",
    urgent:
      "bg-destructive text-white border border-destructive font-semibold shadow-xs animate-pulse",
    muted:
      "bg-muted text-muted-foreground border border-border",
    outline:
      "bg-transparent text-foreground border border-border",
  };

  const isPulse = pulse || variant === "urgent";

  return (
    <span
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${
        isPulse ? "animate-pulse" : ""
      } ${className}`}
      {...props}
    >
      {Icon && <Icon className="w-3 h-3 shrink-0" />}
      {children}
    </span>
  );
};

