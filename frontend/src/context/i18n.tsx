"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import en from "@/locales/en.json";
import vi from "@/locales/vi.json";

export type Locale = "en" | "vi";

type Dictionary = typeof en;

interface I18nContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (keyPath: string) => string;
}

const dictionaries: Record<Locale, Dictionary> = { en, vi };

const I18nContext = createContext<I18nContextType | undefined>(undefined);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    const saved = localStorage.getItem("preferred_locale") as Locale;
    if (saved && (saved === "en" || saved === "vi")) {
      setLocaleState(saved);
    }
  }, []);

  const setLocale = (newLocale: Locale) => {
    setLocaleState(newLocale);
    localStorage.setItem("preferred_locale", newLocale);
  };

  const t = (keyPath: string): string => {
    const keys = keyPath.split(".");
    let curr: unknown = dictionaries[locale] || dictionaries.en;
    for (const k of keys) {
      if (curr && typeof curr === "object" && k in curr) {
        curr = (curr as Record<string, unknown>)[k];
      } else {
        return keyPath;
      }
    }
    return typeof curr === "string" ? curr : keyPath;
  };

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return ctx;
}

