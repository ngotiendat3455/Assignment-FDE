"use client";

import React from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Error403View } from "@/components/organisms/ErrorViews";
import { useI18n } from "@/context/i18n";

export default function Forbidden403Page() {
  const { t } = useI18n();

  return (
    <AppShell title={t("errors.403_title")} subtitle={t("errors.403_desc")}>
      <div className="rounded-2xl border border-border bg-white shadow-xs">
        <Error403View />
      </div>
    </AppShell>
  );
}

