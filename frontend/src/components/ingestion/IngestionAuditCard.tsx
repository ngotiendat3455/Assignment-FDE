"use client";

import React from "react";
import Link from "next/link";
import {
  CheckCircle2,
  ShieldAlert,
  CopyCheck,
  ArrowRight,
  Sparkles,
  RotateCcw,
  Database,
} from "lucide-react";
import { IngestionAuditReport } from "@/types/ingestion";
import { Badge } from "@/components/atoms/Badge";
import { Button } from "@/components/atoms/Button";
import { useI18n } from "@/context/i18n";

export interface IngestionAuditCardProps {
  report: IngestionAuditReport;
  onReset?: () => void;
  resetLabel?: string;
  className?: string;
}

export function IngestionAuditCard({
  report,
  onReset,
  resetLabel,
  className = "",
}: IngestionAuditCardProps) {
  const { t } = useI18n();

  return (
    <div
      className={`rounded-2xl border border-positive/30 bg-white p-6 sm:p-8 shadow-xs animate-in fade-in-50 duration-200 ${className}`}
    >
      {/* Header Banner */}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-green-50 text-positive">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base font-bold text-foreground">
                {t("ingestion.audit_success_banner_title")}
              </h2>
              <Badge variant="positive" icon={CheckCircle2}>
                {t("ingestion.audit_title")}
              </Badge>
            </div>
            <p className="mt-1 text-xs text-muted-foreground max-w-2xl">
              {t("ingestion.audit_success_banner_desc")}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="outline">
            {report.total_rows} {t("table.records")}
          </Badge>
          {onReset && (
            <Button
              variant="outline"
              size="sm"
              icon={RotateCcw}
              onClick={onReset}
            >
              {resetLabel || t("ingestion.btn_clear_reset")}
            </Button>
          )}
        </div>
      </div>

      {/* 3 Core Metric Stat Cards */}
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* Metric 1: Queued for AI */}
        <div className="rounded-xl border border-border bg-accent p-4">
          <div className="flex items-center gap-2 text-positive">
            <CheckCircle2 className="h-5 w-5 shrink-0" />
            <span className="font-mono text-3xl font-bold">
              {report.queued_for_ai_count}
            </span>
          </div>
          <p className="mt-1.5 text-xs font-semibold text-foreground">
            {t("ingestion.audit_queued")}
          </p>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            Active in autonomous scoring pipeline
          </p>
        </div>

        {/* Metric 2: In-batch Duplicates */}
        <div className="rounded-xl border border-border bg-accent p-4">
          <div className="flex items-center gap-2 text-warning">
            <CopyCheck className="h-5 w-5 shrink-0" />
            <span className="font-mono text-3xl font-bold">
              {report.in_batch_duplicates_skipped}
            </span>
          </div>
          <p className="mt-1.5 text-xs font-semibold text-foreground">
            {t("ingestion.audit_duplicates")}
          </p>
          {report.duplicate_handles.length > 0 ? (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {report.duplicate_handles.map((h) => (
                <span
                  key={h}
                  className="rounded-md bg-amber-50 border border-amber-200 px-2 py-0.5 font-mono text-[11px] font-medium text-amber-800"
                >
                  @{h}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Zero intra-batch collisions
            </p>
          )}
        </div>

        {/* Metric 3: Outreach Ledger Collisions */}
        <div className="rounded-xl border border-border bg-accent p-4">
          <div className="flex items-center gap-2 text-primary">
            <ShieldAlert className="h-5 w-5 shrink-0" />
            <span className="font-mono text-3xl font-bold">
              {report.already_contacted_in_ledger}
            </span>
          </div>
          <p className="mt-1.5 text-xs font-semibold text-foreground">
            {t("ingestion.audit_collisions")}
          </p>
          {report.collision_details.length > 0 ? (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {report.collision_details.map((c) => (
                <span
                  key={c.handle}
                  className="rounded-md bg-primary-light/60 border border-primary/20 px-2 py-0.5 font-mono text-[11px] font-medium text-primary"
                >
                  @{c.handle} ({c.status})
                </span>
              ))}
            </div>
          ) : (
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Zero double-messaging collisions
            </p>
          )}
        </div>
      </div>

      {/* DB Idempotency Information Note if any */}
      {report.already_in_db_skipped > 0 && (
        <div className="mt-4 flex items-center gap-2 rounded-xl border border-border bg-muted/50 px-4 py-2.5 text-xs text-muted-foreground">
          <Database className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span>
            <strong className="text-foreground">{report.already_in_db_skipped}</strong>{" "}
            {t("ingestion.audit_db_skipped")}
          </span>
        </div>
      )}

      {/* Action Footer */}
      <div className="mt-6 flex flex-col gap-3 border-t border-border pt-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          {onReset && (
            <Button
              variant="outline"
              size="md"
              icon={RotateCcw}
              onClick={onReset}
            >
              {resetLabel || t("ingestion.btn_clear_reset")}
            </Button>
          )}
        </div>

        <Link href="/">
          <Button
            variant="primary"
            size="md"
            icon={ArrowRight}
            iconPosition="right"
          >
            {t("ingestion.btn_go_workspace")}
          </Button>
        </Link>
      </div>
    </div>
  );
}
