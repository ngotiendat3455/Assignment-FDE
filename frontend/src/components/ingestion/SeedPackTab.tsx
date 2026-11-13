"use client";

import React, { useState } from "react";
import {
  Zap,
  CheckCircle2,
  ShieldAlert,
  Sparkles,
  Layers,
} from "lucide-react";
import { Button } from "@/components/atoms/Button";
import { Badge } from "@/components/atoms/Badge";
import { useToast } from "@/components/molecules/ToastNotification";
import { IngestionAuditCard } from "@/components/ingestion/IngestionAuditCard";
import { triggerSeedPackIngest } from "@/lib/ingestion-api";
import { IngestionAuditReport } from "@/types/ingestion";
import { useI18n } from "@/context/i18n";

export function SeedPackTab() {
  const { t } = useI18n();
  const { toast } = useToast();
  const [segment, setSegment] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [report, setReport] = useState<IngestionAuditReport | null>(null);

  const handleLoadSeed = async () => {
    setLoading(true);
    try {
      const res = await triggerSeedPackIngest(segment || undefined);
      setReport(res);
      toast(t("ingestion.toast_seed_success"), "success");
    } catch {
      toast(t("errors.500_desc"), "error");
    } finally {
      setLoading(false);
    }
  };

  // When ingestion audit report is available, render it as the primary view
  if (report) {
    return (
      <IngestionAuditCard
        report={report}
        onReset={() => setReport(null)}
        resetLabel={t("ingestion.btn_reset_seed")}
      />
    );
  }

  return (
    <div className="rounded-2xl border border-border bg-white p-6 shadow-xs animate-in fade-in-50 duration-150">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Sparkles className="h-5 w-5" />
            </div>
            <h2 className="text-lg font-bold text-foreground">
              {t("ingestion.seed_title")}
            </h2>
          </div>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            {t("ingestion.seed_desc")}
          </p>
        </div>
        <Badge variant="primary">genai-outreach-pack</Badge>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2">
        <div className="flex items-start gap-3 rounded-xl border border-border bg-accent p-4">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-positive" />
          <span className="text-xs leading-relaxed font-medium text-foreground">
            {t("ingestion.seed_scenario_1")}
          </span>
        </div>
        <div className="flex items-start gap-3 rounded-xl border border-border bg-accent p-4">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          <span className="text-xs leading-relaxed font-medium text-foreground">
            {t("ingestion.seed_scenario_2")}
          </span>
        </div>
        <div className="flex items-start gap-3 rounded-xl border border-border bg-accent p-4">
          <Layers className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
          <span className="text-xs leading-relaxed font-medium text-foreground">
            {t("ingestion.seed_scenario_3")}
          </span>
        </div>
        <div className="flex items-start gap-3 rounded-xl border border-border bg-accent p-4">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
          <span className="text-xs leading-relaxed font-medium text-foreground">
            {t("ingestion.seed_scenario_4")}
          </span>
        </div>
      </div>

      <div className="mt-6 flex flex-col gap-4 border-t border-border pt-5 sm:flex-row sm:items-end sm:justify-between">
        <div className="w-full max-w-md">
          <label
            htmlFor="seed-segment-select"
            className="mb-1.5 block text-xs font-semibold text-foreground"
          >
            {t("ingestion.segment_label")}
          </label>
          <select
            id="seed-segment-select"
            value={segment}
            onChange={(e) => setSegment(e.target.value)}
            className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-foreground focus:border-primary focus:ring-2 focus:ring-primary focus:outline-none"
          >
            <option value="">{t("ingestion.segment_all")}</option>
            <option value="SEG-01: SEA Embodied AI & Robotics">
              {t("ingestion.segment_robotics")}
            </option>
            <option value="SEG-02: LLM Inference & AI Infra">
              {t("ingestion.segment_infra")}
            </option>
            <option value="SEG-03: Enterprise Agentic Workflows">
              {t("ingestion.segment_agentic")}
            </option>
          </select>
        </div>

        <Button
          variant="primary"
          size="lg"
          loading={loading}
          icon={Zap}
          onClick={handleLoadSeed}
          data-testid="seed-ingest-btn"
        >
          {loading
            ? t("ingestion.btn_loading")
            : t("ingestion.btn_load_seed")}
        </Button>
      </div>
    </div>
  );
}
