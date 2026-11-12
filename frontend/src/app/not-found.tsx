"use client";

import React from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Error404View } from "@/components/organisms/ErrorViews";
import { useI18n } from "@/context/i18n";

export default function NotFoundPage() {
  const { t } = useI18n();

  return (
    <AppShell title={t("errors.404_title")} subtitle={t("errors.404_desc")}>
      <div className="rounded-2xl border border-border bg-white shadow-xs">
        <Error404View />
      </div>
    </AppShell>
  );
}

