"use client";

import React, { useState, useRef, useEffect } from "react";
import { User, LogOut, Globe, ChevronDown } from "lucide-react";
import { useI18n } from "@/context/i18n";

export interface TopHeaderProps {
  title: string;
  subtitle?: string;
  userName?: string;
  userRole?: string;
  onLogout?: () => void;
  className?: string;
}

export const TopHeader: React.FC<TopHeaderProps> = ({
  title,
  subtitle,
  userName = "Alex Partner",
  userRole = "General Partner",
  onLogout,
  className = "",
}) => {
  const { locale, setLocale, t } = useI18n();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = async () => {
    setDropdownOpen(false);
    if (onLogout) {
      onLogout();
      return;
    }
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } catch {
      // Ignore network error during logout
    }
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("genai_user");
      document.cookie =
        "session_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;";
      window.location.href = "/login";
    }
  };

  return (
    <header
      className={`h-16 border-b border-border bg-white px-6 flex items-center justify-between shrink-0 select-none z-20 ${className}`}
    >
      {/* Left: Screen Title */}
      <div className="flex flex-col min-w-0">
        <h1 className="text-base font-bold text-foreground tracking-tight truncate">
          {title}
        </h1>
        {subtitle && (
          <p className="text-xs text-muted-foreground truncate">{subtitle}</p>
        )}
      </div>

      {/* Right: Profile & Minimal Menu Controls only */}
      <div className="flex items-center gap-4 shrink-0" ref={dropdownRef}>
        <div className="relative">
          <button
            type="button"
            data-testid="user-menu-btn"
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2.5 p-1.5 rounded-lg hover:bg-muted transition-colors focus:outline-none"
          >
            <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-xs shrink-0">
              <User className="w-4 h-4" />
            </div>

            <div className="hidden sm:flex flex-col text-left">
              <span className="text-xs font-semibold text-foreground leading-tight">
                {userName}
              </span>
              <span className="text-[10px] text-muted-foreground leading-tight">
                {userRole}
              </span>
            </div>

            <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
          </button>

          {/* User Profile Dropdown */}
          {dropdownOpen && (
            <div className="absolute right-0 mt-2 w-56 rounded-xl bg-white border border-border shadow-lg py-1.5 z-50 animate-in fade-in-50 zoom-in-95">
              <div className="px-3 py-2 border-b border-border sm:hidden">
                <p className="text-xs font-semibold text-foreground">{userName}</p>
                <p className="text-[10px] text-muted-foreground">{userRole}</p>
              </div>

              {/* Language Switcher Option */}
              <div className="px-3 py-2 border-b border-border flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 text-muted-foreground">
                  <Globe className="w-3.5 h-3.5" />
                  <span>{t("nav.language")}</span>
                </span>

                <div className="flex items-center gap-1 bg-muted rounded p-0.5 font-medium">
                  <button
                    type="button"
                    data-testid="lang-en-btn"
                    onClick={() => setLocale("en")}
                    className={`px-1.5 py-0.5 rounded text-[10px] transition-colors ${
                      locale === "en" ? "bg-white text-primary shadow-xs font-bold" : "text-muted-foreground"
                    }`}
                  >
                    EN
                  </button>
                  <button
                    type="button"
                    data-testid="lang-vi-btn"
                    onClick={() => setLocale("vi")}
                    className={`px-1.5 py-0.5 rounded text-[10px] transition-colors ${
                      locale === "vi" ? "bg-white text-primary shadow-xs font-bold" : "text-muted-foreground"
                    }`}
                  >
                    VI
                  </button>
                </div>
              </div>

              {/* Logout Option */}
              <button
                type="button"
                data-testid="logout-btn"
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-destructive hover:bg-red-50 transition-colors text-left"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>{t("nav.logout")}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

