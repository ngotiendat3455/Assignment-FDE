"use client";

import React, { useState } from "react";
import { Zap, FileSpreadsheet, Globe } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { Tabs, TabItem } from "@/components/molecules/Tabs";
import { SeedPackTab } from "@/components/ingestion/SeedPackTab";
import { CsvUploadTab } from "@/components/ingestion/CsvUploadTab";
import { LiveXLookupTab } from "@/components/ingestion/LiveXLookupTab";
import { useI18n } from "@/context/i18n";

export default function CandidateIngestionPage() {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<string>("seed");

  const tabItems: TabItem[] = [
    {
      key: "seed",
      label: t("ingestion.tab_seed"),
      icon: Zap,
      count: 20,
    },
    {
      key: "csv",
      label: t("ingestion.tab_csv"),
      icon: FileSpreadsheet,
    },
    {
      key: "live",
      label: t("ingestion.tab_live"),
      icon: Globe,
    },
  ];

  return (
    <AppShell
      title={t("ingestion.page_title")}
      subtitle={t("ingestion.page_subtitle")}
      reviewQueueCount={17}
      needsAttentionCount={3}
    >
      <div className="space-y-6">
        <div className="rounded-2xl border border-border bg-white px-6 pt-2 shadow-xs">
          <Tabs
            variant="line"
            items={tabItems}
            activeKey={activeTab}
            onChange={setActiveTab}
          />
        </div>

        {activeTab === "seed" && <SeedPackTab />}
        {activeTab === "csv" && <CsvUploadTab />}
        {activeTab === "live" && <LiveXLookupTab />}
      </div>
    </AppShell>
  );
}

