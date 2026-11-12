"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  ExternalLink,
  Eye,
  Inbox,
  Lock,
  MessageSquarePlus,
  MessageSquareReply,
  RefreshCw,
  Search,
  Send,
  ShieldAlert,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Zap,
} from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/atoms/Button";
import { Badge } from "@/components/atoms/Badge";
import { Input } from "@/components/atoms/Input";
import { Textarea } from "@/components/atoms/Textarea";
import { ScorePill } from "@/components/atoms/ScorePill";
import { Tabs } from "@/components/molecules/Tabs";
import { StatCard } from "@/components/molecules/StatCard";
import {
  Table,
  TableHeader,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TableLoadingSkeleton,
} from "@/components/organisms/DataTable";
import { Modal, ModalBody, ModalFooter } from "@/components/organisms/Modal";
import { Drawer } from "@/components/organisms/Drawer";
import { Error500View } from "@/components/organisms/ErrorViews";
import { useToast } from "@/components/molecules/ToastNotification";
import { useI18n } from "@/context/i18n";
import {
  CalibrationBadgeCode,
  CalibrationMatrixResponse,
  LedgerEntryItem,
  LedgerFilterCounts,
  LedgerFilterTab,
  LedgerKpiMetrics,
} from "@/types/ledger";
import {
  fetchCalibrationMatrix,
  fetchLedgerEntries,
  markLedgerHandled,
  recordLedgerReply,
} from "@/lib/ledger-api";

export interface LedgerDashboardClientProps {
  defaultTab?: "ledger" | "calibration";
}

export const LedgerDashboardClient: React.FC<LedgerDashboardClientProps> = ({
  defaultTab = "ledger",
}) => {
  const { t } = useI18n();
  const { success, error: toastError } = useToast();

  const [activeMainTab, setActiveMainTab] = useState<"ledger" | "calibration">(
    defaultTab
  );
  const [filterTab, setFilterTab] = useState<LedgerFilterTab>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const [ledgerItems, setLedgerItems] = useState<LedgerEntryItem[]>([]);
  const [ledgerKpi, setLedgerKpi] = useState<LedgerKpiMetrics>({
    dispatched_count: 0,
    replied_count: 0,
    reply_rate: 0,
    needs_attention_count: 0,
    blocked_dm_count: 0,
    dedup_collisions_prevented: 3,
    in_batch_duplicates_merged: 1,
    total_safety_interceptions: 5,
  });
  const [filterCounts, setFilterCounts] = useState<LedgerFilterCounts>({
    all: 0,
    needs_attention: 0,
    replied: 0,
    sent: 0,
    blocked: 0,
  });

  const [calibrationData, setCalibrationData] =
    useState<CalibrationMatrixResponse | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<boolean>(false);

  // Record Reply Modal State (Wireframe 2)
  const [replyModalEntry, setReplyModalEntry] =
    useState<LedgerEntryItem | null>(null);
  const [replyText, setReplyText] = useState<string>("");
  const [replyNeedsAttention, setReplyNeedsAttention] = useState<boolean>(true);
  const [isSavingReply, setIsSavingReply] = useState<boolean>(false);

  // Conversation Detail & Immutable Audit Trail Drawer State (Wireframe 3)
  const [drawerEntry, setDrawerEntry] = useState<LedgerEntryItem | null>(null);
  const [handlingId, setHandlingId] = useState<number | null>(null);

  const loadAllData = useCallback(async () => {
    setIsLoading(true);
    setServerError(false);
    try {
      const [ledgerRes, calRes] = await Promise.all([
        fetchLedgerEntries({
          filter_tab: filterTab,
          search: searchQuery,
        }),
        fetchCalibrationMatrix(),
      ]);
      setLedgerItems(ledgerRes.items);
      setLedgerKpi(ledgerRes.kpi);
      setFilterCounts(ledgerRes.counts);
      setCalibrationData(calRes);
    } catch {
      setServerError(true);
    } finally {
      setIsLoading(false);
    }
  }, [filterTab, searchQuery]);

  useEffect(() => {
    const timer = setTimeout(() => {
      void loadAllData();
    }, 120);
    return () => clearTimeout(timer);
  }, [loadAllData]);

  const openRecordReplyModal = (entry: LedgerEntryItem) => {
    setReplyModalEntry(entry);
    setReplyText(entry.reply_text || "");
    setReplyNeedsAttention(true);
  };

  const handleSaveReply = async () => {
    if (!replyModalEntry || !replyText.trim()) return;
    setIsSavingReply(true);
    try {
      const res = await recordLedgerReply(
        replyModalEntry.id,
        replyText.trim(),
        replyNeedsAttention
      );
      success(
        t("ledger.toast_reply_saved", {
          handle: replyModalEntry.handle,
        })
      );
      setReplyModalEntry(null);
      if (drawerEntry && drawerEntry.id === res.ledger.id) {
        setDrawerEntry(res.ledger);
      }
      await loadAllData();
    } catch (err) {
      toastError(err instanceof Error ? err.message : t("errors.500_title"));
    } finally {
      setIsSavingReply(false);
    }
  };

  const handleMarkHandled = async (entry: LedgerEntryItem) => {
    setHandlingId(entry.id);
    try {
      const res = await markLedgerHandled(entry.id);
      success(t("ledger.toast_marked_handled", { handle: entry.handle }));
      if (drawerEntry && drawerEntry.id === res.ledger.id) {
        setDrawerEntry(res.ledger);
      }
      await loadAllData();
    } catch (err) {
      toastError(err instanceof Error ? err.message : t("errors.500_title"));
    } finally {
      setHandlingId(null);
    }
  };

  const formatShortDate = (iso: string | null): string => {
    if (!iso) return t("workspace.time_recent");
    try {
      const d = new Date(iso);
      return d.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  const renderCalibrationBadge = (code: CalibrationBadgeCode) => {
    switch (code) {
      case "INJECTION_BLOCKED":
        return (
          <Badge variant="positive" icon={ShieldCheck}>
            {t("calibration.badge_injection")}
          </Badge>
        );
      case "SPARSE_FLAGGED":
        return (
          <Badge variant="warning" icon={AlertTriangle}>
            {t("calibration.badge_sparse")}
          </Badge>
        );
      case "CLOSED_DM_CAUGHT":
        return (
          <Badge variant="primary" icon={Lock}>
            {t("calibration.badge_closed_dm")}
          </Badge>
        );
      case "DUPLICATE_MERGED":
        return (
          <Badge variant="muted" icon={ShieldAlert}>
            {t("calibration.badge_duplicate")}
          </Badge>
        );
      case "EXACT_MATCH":
        return (
          <Badge variant="positive" icon={CheckCircle2}>
            {t("calibration.badge_exact")}
          </Badge>
        );
      case "CLOSE_MATCH":
        return <Badge variant="warning">{t("calibration.badge_close")}</Badge>;
      default:
        return (
          <Badge variant="destructive">{t("calibration.badge_mismatch")}</Badge>
        );
    }
  };

  if (serverError) {
    return (
      <AppShell
        title={t("ledger.page_title")}
        subtitle={t("ledger.page_subtitle")}
      >
        <div className="py-12">
          <Error500View onRetry={() => void loadAllData()} />
        </div>
      </AppShell>
    );
  }

  const accuracyPct = calibrationData?.kpi.alignment_accuracy ?? 100;

  return (
    <AppShell
      title={t("ledger.page_title")}
      subtitle={t("ledger.page_subtitle")}
      needsAttentionCount={ledgerKpi.needs_attention_count}
    >
      <div className="space-y-6">
        {/* Top Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-foreground tracking-tight">
              {t("ledger.page_title")}
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              {t("ledger.page_subtitle")}
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              icon={RefreshCw}
              onClick={() => void loadAllData()}
              loading={isLoading}
            >
              {t("ledger.btn_refresh")}
            </Button>
          </div>
        </div>

        {/* Main 2-Tab Navigation: 1. Outreach Ledger & Inbox | 2. Partner Calibration Matrix */}
        <Tabs
          variant="line"
          activeKey={activeMainTab}
          onChange={(key) => setActiveMainTab(key as "ledger" | "calibration")}
          items={[
            {
              key: "ledger",
              label: t("ledger.tab_ledger", { count: filterCounts.all }),
              icon: Inbox,
              count: ledgerKpi.needs_attention_count,
              urgent: ledgerKpi.needs_attention_count > 0,
            },
            {
              key: "calibration",
              label: t("ledger.tab_calibration", { accuracy: accuracyPct }),
              icon: SlidersHorizontal,
            },
          ]}
        />

        {/* TAB 1: OUTREACH LEDGER & INBOX */}
        {activeMainTab === "ledger" && (
          <div className="space-y-6">
            {/* 4 KPI Summary StatCards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                label={t("ledger.kpi_dispatched")}
                value={ledgerKpi.dispatched_count}
                subtext={t("ledger.kpi_dispatched_sub")}
                icon={Send}
                variant="primary"
              />
              <StatCard
                label={t("ledger.kpi_replies")}
                value={`${ledgerKpi.replied_count} (${ledgerKpi.reply_rate}%)`}
                subtext={t("ledger.kpi_replies_sub", {
                  rate: ledgerKpi.reply_rate,
                })}
                icon={MessageSquareReply}
                variant="positive"
              />
              <StatCard
                label={t("ledger.kpi_attention")}
                value={ledgerKpi.needs_attention_count}
                subtext={t("ledger.kpi_attention_sub")}
                icon={AlertTriangle}
                variant={
                  ledgerKpi.needs_attention_count > 0 ? "urgent" : "default"
                }
              />
              <StatCard
                label={t("ledger.kpi_safety")}
                value={ledgerKpi.total_safety_interceptions}
                subtext={t("ledger.kpi_safety_sub", {
                  blocked: ledgerKpi.blocked_dm_count,
                })}
                icon={ShieldCheck}
                variant="default"
              />
            </div>

            {/* Filter Pills & Search Bar */}
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 bg-white p-3.5 rounded-xl border border-border shadow-2xs">
              <Tabs
                variant="pills"
                activeKey={filterTab}
                onChange={(key) => setFilterTab(key as LedgerFilterTab)}
                items={[
                  {
                    key: "all",
                    label: t("ledger.filter_all", { count: filterCounts.all }),
                  },
                  {
                    key: "needs_attention",
                    label: t("ledger.filter_attention", {
                      count: filterCounts.needs_attention,
                    }),
                    urgent: filterCounts.needs_attention > 0,
                  },
                  {
                    key: "replied",
                    label: t("ledger.filter_replied", {
                      count: filterCounts.replied,
                    }),
                  },
                  {
                    key: "sent",
                    label: t("ledger.filter_sent", {
                      count: filterCounts.sent,
                    }),
                  },
                  {
                    key: "blocked",
                    label: t("ledger.filter_blocked", {
                      count: filterCounts.blocked,
                    }),
                  },
                ]}
              />

              <div className="w-full lg:w-80">
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onClear={() => setSearchQuery("")}
                  placeholder={t("ledger.search_placeholder")}
                  icon={Search}
                />
              </div>
            </div>

            {/* Immutable Outreach Ledger DataTable */}
            <Table>
              <TableHeader>
                <tr>
                  <TableHead className="w-36">{t("ledger.col_id")}</TableHead>
                  <TableHead className="w-56">
                    {t("ledger.col_candidate")}
                  </TableHead>
                  <TableHead>{t("ledger.col_sent_message")}</TableHead>
                  <TableHead className="w-44">
                    {t("ledger.col_channel")}
                  </TableHead>
                  <TableHead className="w-64">
                    {t("ledger.col_reply")}
                  </TableHead>
                  <TableHead className="w-60 text-right">
                    {t("ledger.col_actions")}
                  </TableHead>
                </tr>
              </TableHeader>

              <TableBody>
                {isLoading ? (
                  <TableLoadingSkeleton rows={4} colSpan={6} />
                ) : ledgerItems.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center">
                      <div className="max-w-sm mx-auto space-y-1.5">
                        <p className="text-sm font-semibold text-foreground">
                          {t("ledger.empty_title")}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {t("ledger.empty_desc")}
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  ledgerItems.map((entry) => (
                    <TableRow
                      key={entry.id}
                      className={`cursor-pointer ${
                        entry.needs_attention ? "bg-red-50/30" : ""
                      }`}
                      onClick={() => setDrawerEntry(entry)}
                    >
                      {/* Col 1: Out-ID & Timestamp */}
                      <TableCell>
                        <div className="font-mono text-xs font-bold text-foreground">
                          {entry.outreach_id}
                        </div>
                        <div className="text-[11px] text-muted-foreground flex items-center gap-1 mt-1">
                          <Clock className="w-3 h-3 shrink-0" />
                          <span>{formatShortDate(entry.sent_at)}</span>
                        </div>
                      </TableCell>

                      {/* Col 2: Candidate & Needs Attention Badge */}
                      <TableCell>
                        <div className="font-semibold text-foreground text-sm">
                          {entry.candidate_name}
                        </div>
                        <div className="text-xs font-mono text-primary mt-0.5">
                          @{entry.handle}
                        </div>
                        {entry.needs_attention && (
                          <div className="mt-1.5">
                            <Badge variant="urgent" size="sm">
                              {t("ledger.badge_needs_attention")}
                            </Badge>
                          </div>
                        )}
                      </TableCell>

                      {/* Col 3: Sent Message */}
                      <TableCell>
                        <p className="text-xs text-foreground/90 line-clamp-3 leading-relaxed">
                          &ldquo;{entry.sent_message}&rdquo;
                        </p>
                      </TableCell>

                      {/* Col 4: Channel & State */}
                      <TableCell>
                        <div className="flex flex-col items-start gap-1.5">
                          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground">
                            <Zap className="w-3 h-3 text-primary" />
                            {entry.dispatch_mode === "LIVE_X"
                              ? t("ledger.channel_live")
                              : t("ledger.channel_sandbox")}
                          </span>

                          {entry.status === "REPLIED" ? (
                            <Badge variant="positive" size="sm">
                              {t("ledger.badge_replied")}
                            </Badge>
                          ) : entry.status === "BLOCKED" ? (
                            <Badge variant="destructive" size="sm">
                              {t("ledger.badge_blocked")}
                            </Badge>
                          ) : (
                            <Badge variant="primary" size="sm">
                              {t("ledger.badge_sent")}
                            </Badge>
                          )}
                        </div>
                      </TableCell>

                      {/* Col 5: Founder Reply */}
                      <TableCell>
                        {entry.status === "REPLIED" && entry.reply_text ? (
                          <div className="space-y-1">
                            <p className="text-xs font-medium text-foreground line-clamp-3 bg-green-50/70 p-2 rounded-lg border border-positive/20">
                              &ldquo;{entry.reply_text}&rdquo;
                            </p>
                            {entry.replied_at && (
                              <span className="text-[10px] text-muted-foreground block">
                                {formatShortDate(entry.replied_at)}
                              </span>
                            )}
                          </div>
                        ) : entry.status === "BLOCKED" ? (
                          <span className="text-xs text-destructive font-medium">
                            {t("ledger.blocked_no_reply")}
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground italic">
                            {t("ledger.waiting_reply")}
                          </span>
                        )}
                      </TableCell>

                      {/* Col 6: Partner Actions */}
                      <TableCell
                        className="text-right"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="flex flex-wrap items-center justify-end gap-1.5">
                          {entry.status === "SENT" && (
                            <Button
                              variant="primary"
                              size="sm"
                              icon={MessageSquarePlus}
                              onClick={() => openRecordReplyModal(entry)}
                            >
                              {t("ledger.btn_simulate_reply")}
                            </Button>
                          )}

                          {entry.status === "REPLIED" && entry.needs_attention && (
                            <>
                              <a
                                href={`https://x.com/${entry.handle}`}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-primary-light text-primary hover:bg-primary hover:text-white transition-colors"
                              >
                                <ExternalLink className="w-3 h-3" />
                                <span>{t("ledger.btn_chat_on_x")}</span>
                              </a>
                              <Button
                                variant="outline"
                                size="sm"
                                icon={CheckCircle2}
                                loading={handlingId === entry.id}
                                onClick={() => void handleMarkHandled(entry)}
                              >
                                {t("ledger.btn_mark_handled")}
                              </Button>
                            </>
                          )}

                          {entry.status === "REPLIED" &&
                            !entry.needs_attention && (
                              <Badge
                                variant="muted"
                                size="sm"
                                icon={CheckCircle2}
                              >
                                {t("ledger.badge_handled")}
                              </Badge>
                            )}

                          <Button
                            variant="ghost"
                            size="sm"
                            icon={Eye}
                            onClick={() => setDrawerEntry(entry)}
                          >
                            {t("ledger.btn_audit_trail")}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        )}

        {/* TAB 2: PARTNER CALIBRATION MATRIX */}
        {activeMainTab === "calibration" && calibrationData && (
          <div className="space-y-6">
            {/* Calibration Banner */}
            <div className="bg-white rounded-xl border border-border p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-2xs">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <h2 className="text-sm font-bold text-foreground">
                    {t("calibration.banner_title")}
                  </h2>
                </div>
                <p className="text-xs text-muted-foreground">
                  {t("calibration.banner_desc")}
                </p>
              </div>
              <Badge variant="positive" className="text-xs px-3 py-1 shrink-0">
                {calibrationData.kpi.alignment_accuracy}%{" "}
                {t("calibration.badge_exact")}
              </Badge>
            </div>

            {/* 4 Calibration KPI StatCards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                label={t("calibration.kpi_accuracy")}
                value={`${calibrationData.kpi.alignment_accuracy}%`}
                subtext={t("calibration.kpi_accuracy_sub", {
                  aligned: calibrationData.kpi.aligned_count,
                  total: calibrationData.kpi.unique_benchmarked,
                })}
                icon={CheckCircle2}
                variant="positive"
              />
              <StatCard
                label={t("calibration.kpi_benchmarked")}
                value={`${calibrationData.kpi.unique_benchmarked} / ${calibrationData.kpi.unique_benchmarked}`}
                subtext={t("calibration.kpi_benchmarked_sub", {
                  total: calibrationData.kpi.unique_benchmarked,
                  dups: calibrationData.kpi.duplicate_rows_detected,
                })}
                icon={SlidersHorizontal}
                variant="primary"
              />
              <StatCard
                label={t("calibration.kpi_safety")}
                value={`${calibrationData.kpi.safety_blocks_verified} / ${calibrationData.kpi.safety_blocks_total}`}
                subtext={t("calibration.kpi_safety_sub", {
                  verified: calibrationData.kpi.safety_blocks_verified,
                  total: calibrationData.kpi.safety_blocks_total,
                })}
                icon={ShieldCheck}
                variant="positive"
              />
              <StatCard
                label={t("calibration.kpi_delta")}
                value={calibrationData.kpi.mean_score_delta.toFixed(2)}
                subtext={t("calibration.kpi_delta_sub")}
                icon={Sparkles}
                variant="default"
              />
            </div>

            {/* Calibration Matrix Table */}
            <Table>
              <TableHeader>
                <tr>
                  <TableHead className="w-48">
                    {t("calibration.col_profile")}
                  </TableHead>
                  <TableHead className="w-56">
                    {t("calibration.col_segment")}
                  </TableHead>
                  <TableHead className="w-36">
                    {t("calibration.col_ai_score")}
                  </TableHead>
                  <TableHead className="w-36">
                    {t("calibration.col_ref_score")}
                  </TableHead>
                  <TableHead className="w-48">
                    {t("calibration.col_alignment")}
                  </TableHead>
                  <TableHead>{t("calibration.col_notes")}</TableHead>
                </tr>
              </TableHeader>
              <TableBody>
                {calibrationData.items.map((row) => (
                  <TableRow key={row.profile_id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold px-1.5 py-0.5 rounded bg-muted text-foreground">
                          {row.profile_id}
                        </span>
                        <span className="font-semibold text-sm text-foreground">
                          {row.name}
                        </span>
                      </div>
                      <div className="text-xs font-mono text-primary mt-1">
                        @{row.handle}
                      </div>
                    </TableCell>

                    <TableCell>
                      <div className="text-xs font-medium text-foreground">
                        {row.segment}
                      </div>
                      <div className="text-[11px] font-mono text-muted-foreground mt-0.5">
                        {row.case_type}
                      </div>
                    </TableCell>

                    <TableCell>
                      <ScorePill score={row.ai_score} size="sm" />
                    </TableCell>

                    <TableCell>
                      <ScorePill score={row.reference_score} size="sm" />
                    </TableCell>

                    <TableCell>
                      {renderCalibrationBadge(row.badge_code)}
                    </TableCell>

                    <TableCell>
                      <p className="text-xs text-foreground leading-relaxed">
                        {row.ai_reason}
                      </p>
                      {row.partner_note && (
                        <p className="text-[11px] text-muted-foreground mt-1">
                          <span className="font-semibold">
                            {t("calibration.scored_by_prefix")} {row.scored_by}
                          </span>{" "}
                          — {row.partner_note}
                        </p>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {/* WIREFRAME 2: SIMULATE / RECORD FOUNDER REPLY MODAL */}
      <Modal
        isOpen={Boolean(replyModalEntry)}
        onClose={() => setReplyModalEntry(null)}
        title={
          replyModalEntry
            ? t("ledger.modal_reply_title", { handle: replyModalEntry.handle })
            : ""
        }
        subtitle={t("ledger.modal_reply_subtitle")}
        maxWidth="2xl"
      >
        {replyModalEntry && (
          <>
            <ModalBody className="space-y-4">
              {/* Sent DM Preview */}
              <div className="p-3.5 rounded-xl bg-muted/50 border border-border space-y-1.5">
                <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
                  <span>
                    {t("ledger.modal_sent_label", {
                      id: replyModalEntry.outreach_id,
                    })}
                  </span>
                  <span>{formatShortDate(replyModalEntry.sent_at)}</span>
                </div>
                <p className="text-xs text-foreground leading-relaxed">
                  &ldquo;{replyModalEntry.sent_message}&rdquo;
                </p>
              </div>

              {/* Quick Sample Fill Button */}
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground">
                  {t("ledger.modal_reply_input_label")}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  icon={Sparkles}
                  onClick={() => setReplyText(t("ledger.modal_sample_text"))}
                >
                  {t("ledger.modal_btn_fill_sample")}
                </Button>
              </div>

              <Textarea
                rows={4}
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                placeholder={t("ledger.modal_reply_placeholder")}
                maxCharacters={600}
              />

              {/* Urgent Needs Attention Checkbox */}
              <label className="flex items-center gap-2.5 p-3 rounded-lg bg-red-50/70 border border-destructive/20 cursor-pointer">
                <input
                  type="checkbox"
                  checked={replyNeedsAttention}
                  onChange={(e) => setReplyNeedsAttention(e.target.checked)}
                  className="rounded border-border text-primary focus:ring-primary"
                />
                <span className="text-xs font-semibold text-destructive">
                  {t("ledger.modal_checkbox_attention")}
                </span>
              </label>
            </ModalBody>

            <ModalFooter>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setReplyModalEntry(null)}
              >
                {t("ledger.modal_btn_cancel")}
              </Button>
              <Button
                variant="primary"
                size="sm"
                icon={MessageSquareReply}
                loading={isSavingReply}
                disabled={!replyText.trim()}
                onClick={() => void handleSaveReply()}
              >
                {isSavingReply
                  ? t("ledger.modal_btn_saving")
                  : t("ledger.modal_btn_save")}
              </Button>
            </ModalFooter>
          </>
        )}
      </Modal>

      {/* WIREFRAME 3: CONVERSATION & IMMUTABLE AUDIT TRAIL DRAWER */}
      <Drawer
        isOpen={Boolean(drawerEntry)}
        onClose={() => setDrawerEntry(null)}
        title={
          drawerEntry
            ? t("ledger.drawer_title", { handle: drawerEntry.handle })
            : ""
        }
        subtitle={drawerEntry?.outreach_id}
        width="lg"
      >
        {drawerEntry && (
          <div className="space-y-6">
            {/* Candidate Summary Card */}
            <div className="p-4 rounded-xl bg-muted/40 border border-border space-y-2">
              <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                {t("ledger.drawer_profile_header")}
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-bold text-foreground">
                    {drawerEntry.candidate_name} (@{drawerEntry.handle})
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {drawerEntry.candidate_location} •{" "}
                    {drawerEntry.candidate_segment}
                  </div>
                </div>
                {drawerEntry.candidate_fit_score !== null && (
                  <ScorePill score={drawerEntry.candidate_fit_score} size="sm" />
                )}
              </div>
              {drawerEntry.candidate_bio && (
                <p className="text-xs text-foreground/80 pt-1 border-t border-border">
                  {drawerEntry.candidate_bio}
                </p>
              )}
            </div>

            {/* Step-by-Step Immutable Audit Timeline */}
            <div className="space-y-4">
              <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                {t("ledger.drawer_timeline_header")}
              </div>

              {/* Step 1: Approved & Dispatched */}
              <div className="p-4 rounded-xl bg-white border border-border space-y-2.5 shadow-2xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
                    <Send className="w-3.5 h-3.5 text-primary" />
                    {drawerEntry.status === "BLOCKED"
                      ? t("ledger.drawer_step1_blocked")
                      : t("ledger.drawer_step1_title")}
                  </span>
                  <span className="text-[11px] font-mono text-muted-foreground">
                    {formatShortDate(drawerEntry.sent_at)}
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-1.5 text-[11px] bg-muted/40 p-2.5 rounded-lg font-mono">
                  <div>
                    <span className="text-muted-foreground">
                      {t("ledger.drawer_mode_label")}
                    </span>{" "}
                    <span className="font-semibold text-foreground">
                      {drawerEntry.dispatch_mode}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">
                      {t("ledger.drawer_dm_id_label")}
                    </span>{" "}
                    <span className="font-semibold text-foreground">
                      {drawerEntry.external_dm_id}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">
                      {t("ledger.drawer_idempotency_label")}
                    </span>{" "}
                    <span className="font-semibold text-primary">
                      {drawerEntry.idempotency_key}
                    </span>
                  </div>
                </div>

                <p className="text-xs text-foreground leading-relaxed bg-muted/20 p-3 rounded-lg border border-border">
                  &ldquo;{drawerEntry.sent_message}&rdquo;
                </p>
              </div>

              {/* Step 2: Founder Reply */}
              <div
                className={`p-4 rounded-xl border space-y-2.5 ${
                  drawerEntry.status === "REPLIED"
                    ? "bg-green-50/40 border-positive/30"
                    : "bg-muted/20 border-border"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
                    <MessageSquareReply className="w-3.5 h-3.5 text-positive" />
                    {drawerEntry.status === "REPLIED"
                      ? t("ledger.drawer_step2_title")
                      : t("ledger.drawer_step2_waiting")}
                  </span>
                  {drawerEntry.replied_at && (
                    <span className="text-[11px] font-mono text-muted-foreground">
                      {formatShortDate(drawerEntry.replied_at)}
                    </span>
                  )}
                </div>

                {drawerEntry.status === "REPLIED" && drawerEntry.reply_text ? (
                  <>
                    <p className="text-xs font-medium text-foreground leading-relaxed bg-white p-3 rounded-lg border border-positive/20">
                      &ldquo;{drawerEntry.reply_text}&rdquo;
                    </p>
                    <div className="pt-1">
                      {drawerEntry.needs_attention ? (
                        <Badge variant="urgent" size="sm">
                          {t("ledger.drawer_attention_active")}
                        </Badge>
                      ) : (
                        <Badge variant="positive" size="sm">
                          {t("ledger.drawer_attention_resolved")}
                        </Badge>
                      )}
                    </div>
                  </>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    {t("ledger.drawer_step2_waiting_desc")}
                  </p>
                )}
              </div>
            </div>

            {/* Partner Actions */}
            <div className="pt-4 border-t border-border space-y-2.5">
              <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                {t("ledger.drawer_actions_header")}
              </div>

              <div className="flex flex-wrap items-center gap-2.5">
                <a
                  href={`https://x.com/${drawerEntry.handle}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-primary text-white hover:bg-primary/90 transition-colors"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>
                    {t("ledger.drawer_btn_open_x", {
                      handle: drawerEntry.handle,
                    })}
                  </span>
                </a>

                {drawerEntry.status === "SENT" && (
                  <Button
                    variant="outline"
                    size="sm"
                    icon={MessageSquarePlus}
                    onClick={() => openRecordReplyModal(drawerEntry)}
                  >
                    {t("ledger.btn_simulate_reply")}
                  </Button>
                )}

                {drawerEntry.status === "REPLIED" &&
                  drawerEntry.needs_attention && (
                    <Button
                      variant="outline"
                      size="sm"
                      icon={CheckCircle2}
                      loading={handlingId === drawerEntry.id}
                      onClick={() => void handleMarkHandled(drawerEntry)}
                    >
                      {t("ledger.drawer_btn_resolve")}
                    </Button>
                  )}
              </div>
            </div>
          </div>
        )}
      </Drawer>
    </AppShell>
  );
};
