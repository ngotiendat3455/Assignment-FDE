"use client";

import React from "react";
import { I18nProvider } from "@/context/i18n";
import { RuntimeProvider, RuntimeConfig } from "@/context/runtime";
import { ToastProvider } from "@/components/molecules/ToastNotification";

const DEFAULT_RUNTIME: RuntimeConfig = {
  runtimeProfile: "OFFLINE_MOCK",
  dispatchMode: "SANDBOX",
};

export function AppProviders({
  children,
  initialRuntime = DEFAULT_RUNTIME,
}: {
  children: React.ReactNode;
  initialRuntime?: RuntimeConfig;
}) {
  return (
    <RuntimeProvider initialRuntime={initialRuntime}>
      <I18nProvider>
        <ToastProvider>{children}</ToastProvider>
      </I18nProvider>
    </RuntimeProvider>
  );
}

