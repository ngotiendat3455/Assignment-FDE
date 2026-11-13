"use client";

import React, { useState, useEffect } from "react";
import {
  Download,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  Upload,
} from "lucide-react";
import { Button } from "@/components/atoms/Button";
import { Badge } from "@/components/atoms/Badge";
import { FileDropzone } from "@/components/molecules/FileDropzone";
import { useToast } from "@/components/molecules/ToastNotification";
import { IngestionAuditCard } from "@/components/ingestion/IngestionAuditCard";
import {
  SAMPLE_CSV_TEMPLATE,
  runCsvPreflight,
  ingestCsvBatch,
} from "@/lib/ingestion-api";
import { CsvPreflightResponse, IngestionAuditReport } from "@/types/ingestion";
import { useI18n } from "@/context/i18n";

export function CsvUploadTab() {
  const { t } = useI18n();
  const { toast } = useToast();

  const [csvContent, setCsvContent] = useState<string>(SAMPLE_CSV_TEMPLATE);
  const [preflight, setPreflight] = useState<CsvPreflightResponse | null>(null);
  const [dedupEnabled, setDedupEnabled] = useState<boolean>(true);
  const [queueAiEnabled, setQueueAiEnabled] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);
  const [report, setReport] = useState<IngestionAuditReport | null>(null);

  useEffect(() => {
    let active = true;
    runCsvPreflight(csvContent)
      .then((res) => {
        if (active) {
          setPreflight(res);
        }
      })
      .catch(() => {
        if (active) {
          setPreflight(null);
        }
      });
    return () => {
      active = false;
    };
  }, [csvContent]);

  const handleFileSelect = (file: File) => {
    const reader = new FileReader();
    reader.onload = async (ev) => {
      const text = typeof ev.target?.result === "string" ? ev.target.result : "";
      setCsvContent(text);
      setReport(null);
      try {
        const pre = await runCsvPreflight(text);
        setPreflight(pre);
        if (!pre.valid) {
          toast(t("ingestion.toast_preflight_error"), "error");
        }
      } catch {
        toast(t("errors.500_desc"), "error");
      }
    };
    reader.readAsText(file);
  };

  const handleDownloadTemplate = () => {
    const blob = new Blob([SAMPLE_CSV_TEMPLATE], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "genai_fund_candidates_template.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleProcessCsv = async () => {
    if (!preflight || !preflight.valid) {
      toast(t("ingestion.toast_preflight_error"), "error");
      return;
    }
    setLoading(true);
    try {
      const res = await ingestCsvBatch(csvContent, undefined, {
        skipLedgerCollisions: dedupEnabled,
        queueAiEnabled: queueAiEnabled,
      });
      setReport(res);
      toast(t("ingestion.toast_csv_success"), "success");
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
        resetLabel={t("ingestion.btn_reset_csv")}
      />
    );
  }

  return (
    <div className="rounded-2xl border border-border bg-white p-6 shadow-xs animate-in fade-in-50 duration-150">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <FileSpreadsheet className="h-5 w-5" />
            </div>
            <h2 className="text-lg font-bold text-foreground">
              {t("ingestion.csv_title")}
            </h2>
          </div>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            {t("ingestion.csv_desc")}
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          icon={Download}
          onClick={handleDownloadTemplate}
        >
          {t("ingestion.btn_download_template")}
        </Button>
      </div>

      <div className="mt-5">
        <FileDropzone onFileSelect={handleFileSelect} />
      </div>

      {preflight && (
        <div className="mt-6">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-bold tracking-wider text-foreground uppercase">
              {t("ingestion.preflight_title")}
            </span>
            {preflight.valid ? (
              <Badge variant="positive" icon={CheckCircle2}>
                {preflight.total_rows} {t("table.records")} •{" "}
                {t("ingestion.preflight_valid_badge")}
              </Badge>
            ) : (
              <Badge
                variant="destructive"
                icon={AlertTriangle}
                data-testid="preflight-error-banner"
              >
                {preflight.error_message ||
                  t("ingestion.preflight_missing_badge")}
              </Badge>
            )}
          </div>

          <div className="overflow-x-auto rounded-xl border border-border bg-white">
            <table className="w-full text-left text-xs text-foreground">
              <thead className="border-b border-border bg-muted text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
                <tr>
                  <th className="px-3 py-2.5">{t("ingestion.col_line")}</th>
                  <th className="px-3 py-2.5">{t("ingestion.col_handle")}</th>
                  <th className="px-3 py-2.5">{t("ingestion.col_name")}</th>
                  <th className="px-3 py-2.5">{t("ingestion.col_bio")}</th>
                  <th className="px-3 py-2.5">{t("ingestion.col_tweets")}</th>
                  <th className="px-3 py-2.5">
                    {t("ingestion.col_validation")}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {preflight.preview_rows.map((row) => (
                  <tr
                    key={row.line_number}
                    className="hover:bg-accent transition-colors"
                  >
                    <td className="px-3 py-2.5 font-mono text-muted-foreground">
                      {row.line_number}
                    </td>
                    <td className="px-3 py-2.5 font-mono font-semibold text-primary">
                      {row.handle}
                    </td>
                    <td className="px-3 py-2.5 font-medium text-foreground">
                      {row.name}
                    </td>
                    <td className="max-w-xs truncate px-3 py-2.5 text-muted-foreground">
                      {row.bio}
                    </td>
                    <td className="max-w-xs truncate px-3 py-2.5 text-muted-foreground">
                      {row.recent_tweets}
                    </td>
                    <td className="px-3 py-2.5">
                      {row.is_valid ? (
                        <Badge variant="positive" size="sm" icon={CheckCircle2}>
                          {t("ingestion.preflight_valid_badge")}
                        </Badge>
                      ) : (
                        <Badge variant="destructive" size="sm" icon={AlertTriangle}>
                          {row.validation_note}
                        </Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="mt-6 flex flex-col gap-4 border-t border-border pt-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-2 text-xs text-foreground">
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={dedupEnabled}
              onChange={(e) => setDedupEnabled(e.target.checked)}
              className="h-4 w-4 rounded border-border text-primary"
            />
            <span>{t("ingestion.opt_dedup")}</span>
          </label>
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={queueAiEnabled}
              onChange={(e) => setQueueAiEnabled(e.target.checked)}
              className="h-4 w-4 rounded border-border text-primary"
            />
            <span>{t("ingestion.opt_queue_ai")}</span>
          </label>
        </div>

        <Button
          variant="primary"
          size="lg"
          disabled={!preflight?.valid}
          loading={loading}
          icon={Upload}
          onClick={handleProcessCsv}
          data-testid="csv-upload-btn"
        >
          {loading
            ? t("ingestion.btn_loading")
            : t("ingestion.btn_process_csv")}
        </Button>
      </div>
    </div>
  );
}
