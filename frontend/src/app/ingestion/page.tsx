"use client";

import React, { useState, useEffect } from "react";
import { Zap, FileSpreadsheet, Globe } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { Tabs, TabItem } from "@/components/molecules/Tabs";
import { SeedPackTab } from "@/components/ingestion/SeedPackTab";
import { CsvUploadTab } from "@/components/ingestion/CsvUploadTab";
import { LiveXLookupTab } from "@/components/ingestion/LiveXLookupTab";
import { useI18n } from "@/context/i18n";
import { fetchStateMachineSummary } from "@/lib/candidates-api";
import { StateMachineSummary } from "@/types/candidate";

export default function CandidateIngestionPage() {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<string>("seed");
  const [summary, setSummary] = useState<StateMachineSummary | null>(null);

  useEffect(() => {
    let active = true;
    fetchStateMachineSummary()
      .then((res) => {
        if (active) setSummary(res);
      })
      .catch(() => {
        if (active) setSummary(null);
      });
    return () => {
      active = false;
    };
  }, [activeTab]);

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
      reviewQueueCount={summary?.state_counts.PENDING_REVIEW ?? 0}
      needsAttentionCount={summary?.ledger_summary.needs_attention_count ?? 0}
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

