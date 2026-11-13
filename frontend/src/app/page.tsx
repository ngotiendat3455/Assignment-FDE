"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  Send,
  Trash2,
  Eye,
  Search,
  RotateCw,
  AlertCircle,
  ShieldCheck,
  CheckCircle2,
  ExternalLink,
  MessageSquare,
} from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/atoms/Button";
import { Badge } from "@/components/atoms/Badge";
import { ScorePill } from "@/components/atoms/ScorePill";
import { StatCard } from "@/components/molecules/StatCard";
import { useToast } from "@/components/molecules/ToastNotification";
import { useI18n } from "@/context/i18n";
import {
  Table,
  TableHeader,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TablePagination,
  TableEmptyState,
} from "@/components/organisms/DataTable";
import { ReviewComposerModal } from "@/components/organisms/ReviewComposerModal";
import { Drawer } from "@/components/organisms/Drawer";
import { Error500View } from "@/components/organisms/ErrorViews";
import {
  CandidateItem,
  StateMachineSummary,
} from "@/types/candidate";
import {
  fetchCandidates,
  fetchStateMachineSummary,
  sendCandidateDm,
  rejectCandidate,
  retryCandidateEvaluation,
  regenerateAiEvaluation,
} from "@/lib/candidates-api";

type FilterTabKey =
  | "ALL"
  | "MATCHES"
  | "PENDING_REVIEW"
  | "SPARSE"
  | "AI_FAILED"
  | "BLOCKED"
  | "SENT"
  | "REJECTED";

export default function HitlReviewWorkspacePage() {
  const { t } = useI18n();
  const { success, error } = useToast();

  // Core Data State
  const [candidates, setCandidates] = useState<CandidateItem[]>([]);
  const [summary, setSummary] = useState<StateMachineSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [hasConnectionError, setHasConnectionError] = useState<boolean>(false);
  const [isProcessingQueue, setIsProcessingQueue] = useState<boolean>(false);

  // Filter & Search State
  const [activeFilterTab, setActiveFilterTab] = useState<FilterTabKey>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Pagination State
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // Review & Composer Modal State
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateItem | null>(null);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState<boolean>(false);

  // Conversation Audit Drawer State
  const [drawerCandidate, setDrawerCandidate] = useState<CandidateItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);

  // Load candidates and state machine summary
  const loadWorkspaceData = useCallback(async () => {
    try {
      setIsLoading(true);
      setHasConnectionError(false);
      const [candidatesData, summaryData] = await Promise.all([
        fetchCandidates(),
        fetchStateMachineSummary(),
      ]);
      setCandidates(candidatesData.items || []);
      setSummary(summaryData);
    } catch {
      setHasConnectionError(true);
      error(t("errors.500_desc"));
    } finally {
      setIsLoading(false);
    }
  }, [error, t]);

  useEffect(() => {
    loadWorkspaceData();
  }, [loadWorkspaceData]);

  // Handle Background Queue Processing Trigger
  const handleProcessQueue = async () => {
    try {
      setIsProcessingQueue(true);
      const API_BASE_URL =
        process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";
      const res = await fetch(`${API_BASE_URL}/queue/process`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: 50 }),
      });
      if (res.ok) {
        success(t("workspace.toast_queue_success"));
        await loadWorkspaceData();
      } else {
        error(t("workspace.toast_queue_error"));
      }
    } catch {
      error(t("errors.500_desc"));
    } finally {
      setIsProcessingQueue(false);
    }
  };

  // Client-side Filter & Search
  const filteredCandidates = useMemo(() => {
    return candidates.filter((item) => {
      // Search matching
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchesQuery =
          item.name.toLowerCase().includes(q) ||
          item.handle.toLowerCase().includes(q) ||
          (item.location || "").toLowerCase().includes(q) ||
          (item.segment || "").toLowerCase().includes(q) ||
          (item.bio || "").toLowerCase().includes(q) ||
          (item.fit_reason || "").toLowerCase().includes(q);
        if (!matchesQuery) return false;
      }

      // Filter Tab matching
      switch (activeFilterTab) {
        case "MATCHES":
          return (item.fit_score ?? 0) >= 3;
        case "PENDING_REVIEW":
          return item.status === "PENDING_REVIEW";
        case "SPARSE":
          return (
            item.status === "INSUFFICIENT_EVIDENCE" ||
            Boolean(item.insufficient_evidence)
          );
        case "AI_FAILED":
          return item.status === "AI_FAILED";
        case "BLOCKED":
          return !item.can_dm || item.status === "SEND_BLOCKED";
        case "SENT":
          return item.status === "SENT" || item.status === "REPLIED";
        case "REJECTED":
          return item.status === "REJECTED";
        case "ALL":
        default:
          return true;
      }
    });
  }, [candidates, searchQuery, activeFilterTab]);

  // Pagination calculation
  const totalItems = filteredCandidates.length;
  const paginatedCandidates = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return filteredCandidates.slice(startIndex, startIndex + pageSize);
  }, [filteredCandidates, currentPage, pageSize]);

  // Fast direct Table Actions
  const handleQuickReject = async (candidate: CandidateItem) => {
    try {
      await rejectCandidate(candidate.id, "Quick rejected from table view");
      success(t("workspace.toast_reject_success", { handle: candidate.handle }));
      await loadWorkspaceData();
    } catch (err) {
      error((err as Error).message || "Failed to reject candidate");
    }
  };

  const handleRetryAi = async (candidate: CandidateItem) => {
    try {
      await retryCandidateEvaluation(candidate.id);
      success(t("workspace.toast_retry_success", { handle: candidate.handle }));
      await loadWorkspaceData();
    } catch (err) {
      error((err as Error).message || "Failed to retry evaluation");
    }
  };

  const handleOpenReviewModal = (candidate: CandidateItem) => {
    setSelectedCandidate(candidate);
    setIsReviewModalOpen(true);
  };

  const handleOpenDrawer = (candidate: CandidateItem) => {
    setDrawerCandidate(candidate);
    setIsDrawerOpen(true);
  };

  // Actions invoked from ReviewComposerModal
  const handleApproveAndSend = async (
    candidateId: number,
    customMessage: string,
    mode: string
  ) => {
    try {
      const res = await sendCandidateDm(candidateId, {
        custom_message: customMessage,
        dispatch_mode: mode,
      });
      success(
        t("workspace.toast_send_success", { handle: res.candidate.handle })
      );
      await loadWorkspaceData();
    } catch (err) {
      error((err as Error).message || "Dispatch failed");
      throw err;
    }
  };

  const handleModalReject = async (candidateId: number) => {
    try {
      const rejected = await rejectCandidate(candidateId);
      success(
        t("workspace.toast_reject_success", {
          handle: rejected.handle,
        })
      );
      await loadWorkspaceData();
    } catch (err) {
      error((err as Error).message || "Rejection failed");
      throw err;
    }
  };

  const handleModalRegenerate = async (candidateId: number) => {
    try {
      const res = await regenerateAiEvaluation(candidateId);
      setSelectedCandidate(res.candidate);
      success(t("workspace.toast_regenerate_success"));
      await loadWorkspaceData();
    } catch (err) {
      error((err as Error).message || "Failed to regenerate AI draft");
      throw err;
    }
  };

  const handleModalRetryEvaluation = async (candidateId: number) => {
    try {
      const updated = await retryCandidateEvaluation(candidateId);
      setSelectedCandidate(updated);
      success(t("workspace.toast_retry_success", { handle: updated.handle }));
      await loadWorkspaceData();
    } catch (err) {
      error((err as Error).message || "Failed to retry evaluation");
      throw err;
    }
  };

  // Status Badge helper
  const renderStatusBadge = (candidate: CandidateItem) => {
    switch (candidate.status) {
      case "REPLIED":
        return (
          <Badge variant="outline" className="border-blue-400 text-blue-700 bg-blue-50 font-bold">
            {t("status.replied")}
          </Badge>
        );
      case "SENT":
        return (
          <Badge variant="outline" className="border-emerald-400 text-emerald-800 bg-emerald-50 font-semibold">
            {t("status.sent")}
          </Badge>
        );
      case "PENDING_REVIEW":
        return (
          <Badge variant="outline" className="border-amber-400 text-amber-900 bg-amber-50 font-semibold">
            {t("status.needs_human")}
          </Badge>
        );
      case "SEND_BLOCKED":
        return (
          <Badge variant="destructive" className="font-semibold text-xs">
            {t("status.blocked")}
          </Badge>
        );
      case "INSUFFICIENT_EVIDENCE":
        return (
          <Badge variant="outline" className="border-amber-300 text-amber-800 bg-amber-50 text-xs">
            {t("status.sparse")}
          </Badge>
        );
      case "AI_FAILED":
        return (
          <Badge variant="destructive" className="bg-rose-600 text-white text-xs">
            {t("status.ai_failed")}
          </Badge>
        );
      case "REJECTED":
        return (
          <Badge variant="muted" className="text-muted-foreground text-xs line-through">
            {t("status.rejected")}
          </Badge>
        );
      case "APPROVED_QUEUED":
        return (
          <Badge variant="outline" className="border-purple-300 text-purple-800 bg-purple-50 font-semibold text-xs">
            {t("status.queued_send")}
          </Badge>
        );
      case "QUEUED_FOR_AI":
      default:
        return (
          <Badge variant="muted" className="font-mono text-xs">
            {t("status.queued_ai")}
          </Badge>
        );
    }
  };

  // Counts for filter pills
  const counts = useMemo(() => {
    return {
      all: candidates.length,
      matches: candidates.filter((c) => (c.fit_score ?? 0) >= 3).length,
      pending: candidates.filter((c) => c.status === "PENDING_REVIEW").length,
      sparse: candidates.filter(
        (c) =>
          c.status === "INSUFFICIENT_EVIDENCE" ||
          Boolean(c.insufficient_evidence)
      ).length,
      ai_failed: candidates.filter((c) => c.status === "AI_FAILED").length,
      blocked: candidates.filter(
        (c) => !c.can_dm || c.status === "SEND_BLOCKED"
      ).length,
      sent: candidates.filter((c) => c.status === "SENT" || c.status === "REPLIED").length,
      rejected: candidates.filter((c) => c.status === "REJECTED").length,
    };
  }, [candidates]);

  if (hasConnectionError) {
    return (
      <AppShell
        title={t("workspace.title")}
        subtitle={t("workspace.subtitle")}
      >
        <Error500View onRetry={loadWorkspaceData} />
      </AppShell>
    );
  }

  return (
    <AppShell
      title={t("workspace.title")}
      subtitle={t("workspace.subtitle")}
      reviewQueueCount={summary?.state_counts.PENDING_REVIEW ?? counts.pending}
      needsAttentionCount={summary?.ledger_summary.needs_attention_count ?? 0}
    >
      <div className="space-y-6">
        {/* Top KPI Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            icon={Send}
            label={t("kpi.dispatched")}
            value={String(summary?.ledger_summary.total_dispatched ?? counts.sent)}
            subtext={t("kpi.dispatched_sub")}
            variant="primary"
            testId="kpi-dispatched"
          />
          <StatCard
            icon={MessageSquare}
            label={t("kpi.replied")}
            value={String(summary?.ledger_summary.total_replied ?? 0)}
            subtext={t("kpi.replied_sub")}
            variant="positive"
            testId="kpi-replied"
          />
          <StatCard
            icon={AlertCircle}
            label={t("kpi.urgent")}
            value={String(summary?.ledger_summary.needs_attention_count ?? 0)}
            subtext={t("kpi.urgent_sub")}
            variant="urgent"
            testId="kpi-urgent"
          />
          <StatCard
            icon={ShieldCheck}
            label={t("kpi.blocked")}
            value={String(summary?.ledger_summary.total_blocked ?? counts.blocked)}
            subtext={t("kpi.blocked_sub")}
            variant="default"
            testId="kpi-blocked"
          />
        </div>

        {/* Search Bar & Action Controls */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-white p-3 rounded-xl border border-border shadow-xs">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              data-testid="workspace-search-input"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              placeholder={t("workspace.search_placeholder")}
              className="w-full pl-9 pr-4 py-2 text-xs bg-muted/30 border border-border rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-hidden focus:ring-1 focus:ring-primary focus:bg-white transition-all"
            />
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleProcessQueue}
              loading={isProcessingQueue}
              data-testid="process-queue-btn"
              className="text-xs shrink-0"
            >
              <RotateCw className="w-3.5 h-3.5 mr-1.5" />
              {t("workspace.btn_process_queue")}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={loadWorkspaceData}
              loading={isLoading}
              data-testid="refresh-workspace-btn"
              className="text-xs shrink-0"
            >
              <RotateCw className="w-3.5 h-3.5 mr-1.5" />
              {t("workspace.btn_refresh")}
            </Button>
          </div>
        </div>

        {/* Filter Pills (Wireframe 1) */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs select-none scrollbar-none">
          <button
            data-testid="filter-pill-ALL"
            onClick={() => {
              setActiveFilterTab("ALL");
              setCurrentPage(1);
            }}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all shrink-0 ${
              activeFilterTab === "ALL"
                ? "bg-primary text-white shadow-xs"
                : "bg-white text-muted-foreground border border-border hover:bg-muted/40"
            }`}
          >
            {t("workspace.tab_all")} ({counts.all})
          </button>

          <button
            data-testid="filter-pill-MATCHES"
            onClick={() => {
              setActiveFilterTab("MATCHES");
              setCurrentPage(1);
            }}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all shrink-0 flex items-center gap-1.5 ${
              activeFilterTab === "MATCHES"
                ? "bg-emerald-700 text-white shadow-xs"
                : "bg-white text-muted-foreground border border-border hover:bg-muted/40"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            {t("workspace.tab_matches")} ({counts.matches})
          </button>

          <button
            data-testid="filter-pill-PENDING_REVIEW"
            onClick={() => {
              setActiveFilterTab("PENDING_REVIEW");
              setCurrentPage(1);
            }}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all shrink-0 flex items-center gap-1.5 ${
              activeFilterTab === "PENDING_REVIEW"
                ? "bg-amber-700 text-white shadow-xs"
                : "bg-white text-muted-foreground border border-border hover:bg-muted/40"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            {t("workspace.tab_pending")} ({counts.pending})
          </button>

          <button
            data-testid="filter-pill-SPARSE"
            onClick={() => {
              setActiveFilterTab("SPARSE");
              setCurrentPage(1);
            }}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all shrink-0 flex items-center gap-1.5 ${
              activeFilterTab === "SPARSE"
                ? "bg-amber-600 text-white shadow-xs"
                : "bg-white text-muted-foreground border border-border hover:bg-muted/40"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            {t("workspace.tab_sparse")} ({counts.sparse})
          </button>

          <button
            data-testid="filter-pill-AI_FAILED"
            onClick={() => {
              setActiveFilterTab("AI_FAILED");
              setCurrentPage(1);
            }}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all shrink-0 flex items-center gap-1.5 ${
              activeFilterTab === "AI_FAILED"
                ? "bg-rose-700 text-white shadow-xs"
                : "bg-white text-muted-foreground border border-border hover:bg-muted/40"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-rose-600" />
            {t("workspace.tab_ai_failed")} ({counts.ai_failed})
          </button>

          <button
            data-testid="filter-pill-BLOCKED"
            onClick={() => {
              setActiveFilterTab("BLOCKED");
              setCurrentPage(1);
            }}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all shrink-0 flex items-center gap-1.5 ${
              activeFilterTab === "BLOCKED"
                ? "bg-rose-700 text-white shadow-xs"
                : "bg-white text-muted-foreground border border-border hover:bg-muted/40"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            {t("workspace.tab_blocked")} ({counts.blocked})
          </button>

          <button
            data-testid="filter-pill-SENT"
            onClick={() => {
              setActiveFilterTab("SENT");
              setCurrentPage(1);
            }}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all shrink-0 flex items-center gap-1.5 ${
              activeFilterTab === "SENT"
                ? "bg-blue-700 text-white shadow-xs"
                : "bg-white text-muted-foreground border border-border hover:bg-muted/40"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            {t("workspace.tab_sent")} ({counts.sent})
          </button>

          <button
            data-testid="filter-pill-REJECTED"
            onClick={() => {
              setActiveFilterTab("REJECTED");
              setCurrentPage(1);
            }}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all shrink-0 flex items-center gap-1.5 ${
              activeFilterTab === "REJECTED"
                ? "bg-gray-800 text-white shadow-xs"
                : "bg-white text-muted-foreground border border-border hover:bg-muted/40"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-gray-400" />
            {t("workspace.tab_rejected")} ({counts.rejected})
          </button>
        </div>

        {/* Table-First Candidate Canvas */}
        <div className="bg-white rounded-2xl border border-border shadow-xs overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12 text-center">#</TableHead>
                <TableHead>{t("table.col_candidate")}</TableHead>
                <TableHead>{t("table.col_track")}</TableHead>
                <TableHead>{t("table.col_score")}</TableHead>
                <TableHead>{t("table.col_status")}</TableHead>
                <TableHead className="text-right">{t("table.col_actions")}</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {paginatedCandidates.length === 0 ? (
                <TableEmptyState
                  title={t("table.empty_title")}
                  description={t("table.empty_desc")}
                  colSpan={6}
                />
              ) : (
                paginatedCandidates.map((c, index) => {
                  const serialNumber = (currentPage - 1) * pageSize + index + 1;
                  const isTerminal = c.status === "SENT" || c.status === "REPLIED";

                  return (
                    <TableRow key={c.id} data-testid={`candidate-row-${c.handle}`}>
                      {/* Index */}
                      <TableCell className="text-center font-mono text-xs text-muted-foreground">
                        {serialNumber}
                      </TableCell>

                      {/* Candidate Avatar & Handle */}
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-primary/10 text-primary font-bold text-xs flex items-center justify-center shrink-0">
                            {c.name.slice(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <div className="flex items-center gap-1.5">
                              <span className="font-semibold text-foreground text-xs">
                                {c.name}
                              </span>
                              {c.needs_attention && (
                                <Badge variant="urgent" size="sm">
                                  {t("status.urgent_tag")}
                                </Badge>
                              )}
                            </div>
                            <a
                              href={`https://x.com/${c.handle}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-primary hover:underline font-mono text-[11px] flex items-center gap-1"
                            >
                              @{c.handle}
                              <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                            </a>
                          </div>
                        </div>
                      </TableCell>

                      {/* Location & Segment */}
                      <TableCell>
                        <div className="text-xs text-foreground font-medium">
                          {c.segment || t("workspace.default_segment")}
                        </div>
                        <div className="text-[11px] text-muted-foreground">
                          {c.location || t("workspace.default_location")}
                        </div>
                      </TableCell>

                      {/* AI Score */}
                      <TableCell>
                        <ScorePill score={c.fit_score} showIcon size="sm" />
                      </TableCell>

                      {/* Lifecycle Status */}
                      <TableCell
                        data-testid={`candidate-status-${c.handle}`}
                        data-status={c.status}
                      >
                        {renderStatusBadge(c)}
                      </TableCell>

                      {/* Fast Action Buttons */}
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* If AI Failed: Show Retry Button */}
                          {c.status === "AI_FAILED" && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleRetryAi(c)}
                              data-testid={`retry-btn-${c.handle}`}
                              className="text-amber-700 border-amber-300 hover:bg-amber-50 h-7 text-xs"
                            >
                              <RotateCw className="w-3 h-3 mr-1" />
                              {t("actions.retry")}
                            </Button>
                          )}

                          {/* If Replied/Has History: Can open Drawer */}
                          {c.status === "REPLIED" && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleOpenDrawer(c)}
                              data-testid={`crm-btn-${c.handle}`}
                              className="text-blue-700 border-blue-300 hover:bg-blue-50 h-7 text-xs"
                            >
                              <MessageSquare className="w-3 h-3 mr-1 text-blue-600" />
                              {t("workspace.view_crm")}
                            </Button>
                          )}

                          {/* Primary Action: Review & Approve */}
                          <Button
                            size="sm"
                            variant="primary"
                            onClick={() => handleOpenReviewModal(c)}
                            data-testid={`review-btn-${c.handle}`}
                            className="bg-primary hover:bg-primary/90 h-7 text-xs font-medium"
                          >
                            <Eye className="w-3 h-3 mr-1" />
                            {t("actions.view_review")}
                          </Button>

                          {/* Quick Reject Button (Disabled if already sent/replied) */}
                          <button
                            onClick={() => handleQuickReject(c)}
                            disabled={isTerminal || c.status === "REJECTED"}
                            data-testid={`reject-btn-${c.handle}`}
                            title={t("actions.reject")}
                            className="p-1.5 rounded-md text-muted-foreground hover:text-rose-600 hover:bg-rose-50 disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-muted-foreground transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>

          {/* Table Pagination Controls */}
          {totalItems > 0 && (
            <TablePagination
              currentPage={currentPage}
              pageSize={pageSize}
              totalItems={totalItems}
              pageSizeOptions={[10, 25, 50]}
              onPageChange={setCurrentPage}
              onPageSizeChange={(size) => {
                setPageSize(size);
                setCurrentPage(1);
              }}
            />
          )}
        </div>
      </div>

      {/* Review & Grounded DM Composer Modal */}
      <ReviewComposerModal
        isOpen={isReviewModalOpen}
        onClose={() => setIsReviewModalOpen(false)}
        candidate={selectedCandidate}
        onApproveAndSend={handleApproveAndSend}
        onReject={handleModalReject}
        onRegenerate={handleModalRegenerate}
        onRetryEvaluation={handleModalRetryEvaluation}
      />

      {/* Conversation Trail Drawer for REPLIED / CRM Candidates */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={t("drawer.audit_title")}
        subtitle={drawerCandidate ? `${drawerCandidate.name} (@${drawerCandidate.handle})` : ""}
      >
        {drawerCandidate && (
          <div className="space-y-6">
            {drawerCandidate.needs_attention && (
              <div className="bg-amber-50 border border-amber-300 rounded-xl p-4">
                <div className="flex items-center gap-2 text-amber-900 font-bold text-xs mb-1">
                  <AlertCircle className="w-4 h-4 text-amber-600" />
                  {t("drawer.urgent_alert")}
                </div>
                <p className="text-xs text-amber-800">
                  {t("drawer.urgent_desc")}
                </p>
              </div>
            )}

            <div className="space-y-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                {t("drawer.timeline_title")}
              </h4>

              {/* Sent Message */}
              <div className="bg-muted/40 rounded-xl p-4 border border-border space-y-2">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span className="font-semibold text-foreground">
                    GenAI Fund Partner (Outreach)
                  </span>
                  <span>{drawerCandidate.sent_at || t("workspace.time_recent")}</span>
                </div>
                <p className="text-xs text-foreground/90 leading-relaxed font-sans">
                  {drawerCandidate.sent_message || t("workspace.historical_message")}
                </p>
                <div className="text-[11px] text-emerald-700 font-medium flex items-center gap-1 pt-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  {t("drawer.dm_delivered")}
                </div>
              </div>

              {/* Reply Received */}
              {drawerCandidate.reply_text && (
                <div className="bg-blue-50/60 rounded-xl p-4 border border-blue-200 space-y-2">
                  <div className="flex items-center justify-between text-xs text-blue-900">
                    <span className="font-bold">
                      {drawerCandidate.name} (@{drawerCandidate.handle})
                    </span>
                    <span className="text-muted-foreground">
                      {drawerCandidate.replied_at || t("workspace.time_recent")}
                    </span>
                  </div>
                  <p className="text-xs text-blue-950 leading-relaxed font-sans font-medium">
                    &ldquo;{drawerCandidate.reply_text}&rdquo;
                  </p>
                  <div className="text-[11px] text-blue-700 font-medium flex items-center gap-1 pt-1">
                    <MessageSquare className="w-3.5 h-3.5" />
                    {t("drawer.founder_reply")}
                  </div>
                </div>
              )}
            </div>

            <div className="pt-4 border-t border-border flex flex-col gap-2">
              <a
                href={`https://x.com/messages`}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full inline-flex items-center justify-center py-2 px-3 rounded-lg bg-primary text-white text-xs font-semibold hover:bg-primary/90 transition-colors gap-1.5"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                {t("drawer.open_x")}
              </a>
            </div>
          </div>
        )}
      </Drawer>
    </AppShell>
  );
}
