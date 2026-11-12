"use client";

import React from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Error500View } from "@/components/organisms/ErrorViews";
import { useI18n } from "@/context/i18n";

export default function GlobalAppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const { t } = useI18n();

  return (
    <AppShell title={t("errors.500_title")} subtitle={t("errors.500_desc")}>
      <div className="rounded-2xl border border-border bg-white shadow-xs">
        <Error500View errorMessage={error.message} onRetry={reset} />
      </div>
    </AppShell>
  );
}

