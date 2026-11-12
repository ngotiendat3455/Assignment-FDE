"use client";

import React from "react";
import { I18nProvider } from "@/context/i18n";
import { ToastProvider } from "@/components/molecules/ToastNotification";

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <I18nProvider>
      <ToastProvider>{children}</ToastProvider>
    </I18nProvider>
  );
}

