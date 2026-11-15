"use client";

import React, { useState } from "react";
import {
  Download,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  Info,
  Globe,
  ClipboardPaste,
  Upload,
} from "lucide-react";
import { Button } from "@/components/atoms/Button";
import { Badge } from "@/components/atoms/Badge";
import { FileDropzone } from "@/components/molecules/FileDropzone";
import { useToast } from "@/components/molecules/ToastNotification";
import { IngestionAuditCard } from "@/components/ingestion/IngestionAuditCard";
import {
  getCsvTemplateForRuntime,
  normalizePastedHandlesToCsv,
  runCsvPreflight,
  ingestCsvBatch,
} from "@/lib/ingestion-api";
import { CsvPreflightResponse, IngestionAuditReport } from "@/types/ingestion";
import { useI18n } from "@/context/i18n";
import { useRuntime } from "@/context/runtime";

const REQUIRED_CSV_COLUMNS = ["handle", "name", "bio", "recent_tweets"] as const;

function renderDedupBadge(dedupStatus?: string) {
  switch (dedupStatus) {
    case "IN_BATCH_DUPLICATE":
      return <Badge variant="warning" size="sm">Duplicate in CSV</Badge>;
    case "ALREADY_IN_DB":
      return <Badge variant="muted" size="sm">Already in DB</Badge>;
    case "ALREADY_CONTACTED":
      return <Badge variant="destructive" size="sm">Blocked: Ledger</Badge>;
    case "INVALID":
      return <Badge variant="destructive" size="sm">Invalid</Badge>;
    default:
      return <Badge variant="positive" size="sm">New</Badge>;
  }
}

export function CsvUploadTab() {
  const { t } = useI18n();
  const { runtimeProfile } = useRuntime();
  const isLiveProduction = runtimeProfile === "LIVE_PRODUCTION";
  const { toast } = useToast();

  const [csvContent, setCsvContent] = useState<string>("");
  const [pasteOpen, setPasteOpen] = useState<boolean>(false);
  const [pasteInput, setPasteInput] = useState<string>("");
  const [preflight, setPreflight] = useState<CsvPreflightResponse | null>(null);
  const [dedupEnabled, setDedupEnabled] = useState<boolean>(true);
  const [queueAiEnabled, setQueueAiEnabled] = useState<boolean>(true);
  const [verifyWithX, setVerifyWithX] = useState<boolean>(
    runtimeProfile === "LIVE_PRODUCTION"
  );
  const [previewingX, setPreviewingX] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [report, setReport] = useState<IngestionAuditReport | null>(null);

  const handleClearCsv = () => {
    setCsvContent("");
    setPreflight(null);
    setReport(null);
  };

  const executePreflight = async (
    rawCsv: string,
    useVerifyX: boolean,
    fetchLivePreview: boolean = false
  ) => {
    const pre = await runCsvPreflight(rawCsv, useVerifyX, fetchLivePreview);
    setPreflight(pre);
    if (!pre.valid) {
      toast(pre.error_message || t("ingestion.toast_preflight_error"), "error");
    }
    return pre;
  };

  const handleToggleVerifyWithX = async (checked: boolean) => {
    setVerifyWithX(checked);
    if (csvContent.trim()) {
      try {
        await executePreflight(csvContent, checked, false);
      } catch {
        // Ignore transient preflight error on toggle
      }
    }
  };

  const handleFileSelect = (file: File) => {
    const reader = new FileReader();
    reader.onload = async (ev) => {
      const text = typeof ev.target?.result === "string" ? ev.target.result : "";
      setCsvContent(text);
      setReport(null);
      try {
        await executePreflight(text, verifyWithX, false);
      } catch (err) {
        toast(
          err instanceof Error && err.message ? err.message : t("errors.500_desc"),
          "error"
        );
      }
    };
    reader.readAsText(file);
  };

  const handleApplyPastedHandles = async () => {
    const normalizedCsv = normalizePastedHandlesToCsv(pasteInput);
    if (!normalizedCsv) {
      toast(t("ingestion.toast_preflight_error"), "error");
      return;
    }
    setCsvContent(normalizedCsv);
    setReport(null);
    try {
      await executePreflight(normalizedCsv, verifyWithX, false);
    } catch (err) {
      toast(
        err instanceof Error && err.message ? err.message : t("errors.500_desc"),
        "error"
      );
    }
  };

  const handlePreviewLiveX = async () => {
    if (!csvContent.trim()) return;
    setPreviewingX(true);
    try {
      await executePreflight(csvContent, true, true);
    } catch (err) {
      toast(
        err instanceof Error && err.message ? err.message : t("errors.500_desc"),
        "error"
      );
    } finally {
      setPreviewingX(false);
    }
  };

  const handleDownloadTemplate = () => {
    const template = getCsvTemplateForRuntime(runtimeProfile, verifyWithX);
    const blob = new Blob([template.content], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", template.filename);
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
        verifyWithXApi: verifyWithX,
      });
      setReport(res);
      toast(t("ingestion.toast_csv_success"), "success");
    } catch (err) {
      toast(
        err instanceof Error && err.message ? err.message : t("errors.500_desc"),
        "error"
      );
    } finally {
      setLoading(false);
    }
  };

  // When ingestion audit report is available, render it as the primary view
  if (report) {
    return (
      <IngestionAuditCard
        report={report}
        onReset={handleClearCsv}
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
            {verifyWithX
              ? t("ingestion.csv_desc_live_x")
              : t("ingestion.csv_desc")}
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          icon={Download}
          onClick={handleDownloadTemplate}
          data-testid="csv-download-template-btn"
        >
          {isLiveProduction
            ? t("ingestion.btn_download_template_live")
            : t("ingestion.btn_download_template_mock")}
        </Button>
      </div>

      {isLiveProduction && (
        <div
          data-testid="live-csv-policy-note"
          className="mt-4 flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50/70 px-4 py-3 text-xs text-amber-950"
        >
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
          <div className="space-y-0.5">
            <p className="font-semibold text-amber-900">
              {t("ingestion.live_csv_note_title")}
            </p>
            <p className="leading-relaxed text-amber-800">
              {t("ingestion.live_csv_note_body")}
            </p>
          </div>
        </div>
      )}

      <div className="mt-5">
        <FileDropzone
          onFileSelect={handleFileSelect}
          onClear={handleClearCsv}
        />

        <div className="mt-3">
          <button
            type="button"
            data-testid="csv-paste-toggle"
            onClick={() => setPasteOpen((prev) => !prev)}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
          >
            <ClipboardPaste className="h-3.5 w-3.5" />
            <span>{t("ingestion.paste_toggle_label")}</span>
          </button>

          {pasteOpen && (
            <div className="mt-2.5 space-y-2 rounded-xl border border-border bg-accent/50 p-3.5">
              <textarea
                rows={4}
                data-testid="csv-paste-textarea"
                value={pasteInput}
                onChange={(e) => setPasteInput(e.target.value)}
                placeholder={"handle,segment\nelonmusk,\njennierubjane,\nJensenHuang,\n@your_test_handle,SEG-01: SEA Embodied AI & Robotics"}
                className="w-full rounded-lg border border-border bg-white p-2.5 font-mono text-xs text-foreground focus:border-primary focus:ring-2 focus:ring-primary/20 focus:outline-none"
              />
              <div className="flex justify-end">
                <Button
                  variant="outline"
                  size="sm"
                  data-testid="csv-paste-apply-btn"
                  onClick={() => void handleApplyPastedHandles()}
                >
                  {t("ingestion.paste_apply_btn")}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {preflight && (
        <div className="mt-6 space-y-4">
          <div
            data-testid="csv-column-status"
            className="rounded-xl border border-border bg-accent/60 p-4"
          >
            <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-bold tracking-wider text-foreground uppercase">
                {t("ingestion.csv_columns_status")}
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

            <div className="flex flex-wrap gap-2">
              {REQUIRED_CSV_COLUMNS.map((col) => {
                const isRequired = !verifyWithX || col === "handle";
                const isMissing = isRequired && preflight.missing_columns.includes(col);
                const isSyncedViaX = !isRequired && verifyWithX;
                return (
                  <span
                    key={col}
                    data-testid={`col-status-${col}`}
                    className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 font-mono text-xs font-medium ${
                      isMissing
                        ? "border-red-200 bg-red-50 text-red-700"
                        : isSyncedViaX
                          ? "border-sky-200 bg-sky-50 text-sky-700"
                          : "border-emerald-200 bg-emerald-50 text-emerald-700"
                    }`}
                  >
                    {isMissing ? (
                      <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                    ) : (
                      <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                    )}
                    <span>{col}</span>
                    <span className="font-sans text-[11px] font-semibold">
                      ({isMissing
                        ? t("ingestion.col_status_missing")
                        : isSyncedViaX
                          ? t("ingestion.col_status_x_sync")
                          : t("ingestion.col_status_found")})
                    </span>
                  </span>
                );
              })}
            </div>

            {preflight.detected_columns.length > 0 && (
              <div className="mt-3 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                <span className="font-medium">
                  {t("ingestion.detected_headers_label")} (
                  {preflight.detected_columns.length}):
                </span>
                {preflight.detected_columns.map((hdr) => (
                  <span
                    key={hdr}
                    className="rounded border border-border bg-white px-2 py-0.5 font-mono text-[11px] text-foreground"
                  >
                    {hdr}
                  </span>
                ))}
              </div>
            )}
          </div>

          {preflight.total_rows === 0 && preflight.missing_columns.length === 0 ? (
            <div
              data-testid="csv-empty-rows-notice"
              className="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50/70 p-4 text-xs text-amber-950"
            >
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
              <div className="space-y-1">
                <p className="font-semibold text-amber-900">
                  {t("ingestion.empty_rows_title")}
                </p>
                <p className="leading-relaxed text-amber-800">
                  {t("ingestion.empty_rows_desc")}
                </p>
              </div>
            </div>
          ) : preflight.preview_rows.length > 0 && (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-bold tracking-wider text-foreground uppercase">
                    {t("ingestion.preflight_title")}
                  </span>
                  {verifyWithX && preflight.local_dedup_summary && (
                    <Badge variant="muted" size="sm">
                      {preflight.local_dedup_summary.new_handles} new •{" "}
                      {preflight.local_dedup_summary.in_batch_duplicates +
                        preflight.local_dedup_summary.already_in_db +
                        preflight.local_dedup_summary.already_contacted}{" "}
                      deduped ($0)
                    </Badge>
                  )}
                </div>

                {verifyWithX && preflight.valid && (
                  <Button
                    variant="outline"
                    size="sm"
                    icon={Globe}
                    loading={previewingX}
                    disabled={
                      previewingX ||
                      (preflight.local_dedup_summary?.new_handles ?? 0) === 0
                    }
                    onClick={() => void handlePreviewLiveX()}
                    data-testid="csv-preview-x-btn"
                  >
                    {previewingX
                      ? t("ingestion.btn_previewing_live_x")
                      : t("ingestion.btn_preview_live_x")}
                  </Button>
                )}
              </div>

              <div className="overflow-x-auto rounded-xl border border-border bg-white">
                <table className="w-full text-left text-xs text-foreground">
                  <thead className="border-b border-border bg-muted text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
                    {verifyWithX ? (
                      <tr>
                        <th className="px-3 py-2.5">{t("ingestion.col_line")}</th>
                        <th className="px-3 py-2.5">{t("ingestion.col_handle")}</th>
                        <th className="px-3 py-2.5">{t("ingestion.col_segment")}</th>
                        <th className="px-3 py-2.5">{t("ingestion.col_x_profile")}</th>
                        <th className="px-3 py-2.5">{t("ingestion.col_dedup_guard")}</th>
                        <th className="px-3 py-2.5">{t("ingestion.col_validation")}</th>
                      </tr>
                    ) : (
                      <tr>
                        <th className="px-3 py-2.5">{t("ingestion.col_line")}</th>
                        <th className="px-3 py-2.5">{t("ingestion.col_handle")}</th>
                        <th className="px-3 py-2.5">{t("ingestion.col_name")}</th>
                        <th className="px-3 py-2.5">{t("ingestion.col_bio")}</th>
                        <th className="px-3 py-2.5">{t("ingestion.col_tweets")}</th>
                        <th className="px-3 py-2.5">{t("ingestion.col_validation")}</th>
                      </tr>
                    )}
                  </thead>
                  <tbody className="divide-y divide-border">
                    {preflight.preview_rows.map((row) =>
                      verifyWithX ? (
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
                          <td className="max-w-[200px] truncate px-3 py-2.5 text-muted-foreground">
                            {row.segment || "Auto / Default Segment"}
                          </td>
                          <td className="max-w-sm px-3 py-2.5">
                            {row.x_preview_status === "FOUND" ? (
                              <div className="space-y-0.5">
                                <div className="flex flex-wrap items-center gap-1.5 font-medium text-foreground">
                                  <span>{row.name}</span>
                                  {typeof row.followers_count === "number" && (
                                    <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                                      {row.followers_count.toLocaleString()} followers
                                    </span>
                                  )}
                                </div>
                                <p className="truncate text-[11px] text-muted-foreground">
                                  {row.bio}
                                </p>
                              </div>
                            ) : row.x_preview_status === "INVALID" ? (
                              <span className="text-red-700 font-medium">
                                Invalid X handle syntax (will skip on Import)
                              </span>
                            ) : row.x_preview_status === "NOT_FOUND" ? (
                              <span className="text-red-700 font-medium">
                                Account not found on X (will skip)
                              </span>
                            ) : row.x_preview_status === "SKIPPED_DEDUP" ? (
                              <span className="text-muted-foreground italic">
                                Skipped by dedup guard ($0 X API)
                              </span>
                            ) : (
                              <span className="text-muted-foreground">
                                Pending Live X sync (name, bio, 5 tweets on Import)
                              </span>
                            )}
                          </td>
                          <td className="px-3 py-2.5">
                            {renderDedupBadge(row.dedup_status)}
                          </td>
                          <td className="px-3 py-2.5">
                            {row.is_valid ? (
                              <Badge variant="positive" size="sm" icon={CheckCircle2}>
                                {row.validation_note || t("ingestion.preflight_valid_badge")}
                              </Badge>
                            ) : (
                              <Badge variant="destructive" size="sm" icon={AlertTriangle}>
                                {row.validation_note}
                              </Badge>
                            )}
                          </td>
                        </tr>
                      ) : (
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
                      )
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}
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
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              data-testid="csv-verify-x-checkbox"
              checked={verifyWithX}
              onChange={(e) => void handleToggleVerifyWithX(e.target.checked)}
              className="h-4 w-4 rounded border-border text-primary"
            />
            <span>
              Verify &amp; sync profiles live from X API v2{" "}
              <span className="text-muted-foreground">
                (Batch /2/users/by + max 5 posts/user • ~$0.035/new profile • max 25 rows/upload)
              </span>
            </span>
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
