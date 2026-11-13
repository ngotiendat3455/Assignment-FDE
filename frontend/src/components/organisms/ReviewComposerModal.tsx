"use client";

import React, { useState, useEffect } from "react";
import {
  Sparkles,
  Send,
  Trash2,
  RotateCw,
  AlertCircle,
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  ExternalLink,
  MessageSquare,
  Lock,
} from "lucide-react";
import { CandidateItem } from "@/types/candidate";
import { useI18n } from "@/context/i18n";
import { Modal, ModalBody } from "@/components/organisms/Modal";
import { ScorePill } from "@/components/atoms/ScorePill";
import { Badge } from "@/components/atoms/Badge";
import { Button } from "@/components/atoms/Button";
import { Textarea } from "@/components/atoms/Textarea";
import { EvidenceMark } from "@/components/atoms/EvidenceMark";
import { EvidenceCallout } from "@/components/molecules/EvidenceCallout";

export interface ReviewComposerModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidate: CandidateItem | null;
  onApproveAndSend: (
    candidateId: number,
    customMessage: string,
    dispatchMode: string
  ) => Promise<void>;
  onReject: (candidateId: number) => Promise<void>;
  onRegenerate: (candidateId: number) => Promise<void>;
  onRetryEvaluation: (candidateId: number) => Promise<void>;
}

export const ReviewComposerModal: React.FC<ReviewComposerModalProps> = ({
  isOpen,
  onClose,
  candidate,
  onApproveAndSend,
  onReject,
  onRegenerate,
  onRetryEvaluation,
}) => {
  const { t } = useI18n();

  const [dmText, setDmText] = useState("");
  const [dispatchMode, setDispatchMode] = useState<"SANDBOX" | "LIVE_X">("SANDBOX");
  const [isSending, setIsSending] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);

  useEffect(() => {
    if (candidate) {
      setDmText(candidate.edited_dm || candidate.draft_dm || "");
    } else {
      setDmText("");
    }
  }, [candidate]);

  if (!candidate) return null;

  const charCount = dmText.length;
  const isTooShort = charCount > 0 && charCount < 100;
  const isOptimal = charCount >= 250 && charCount <= 600;
  const isExceeded = charCount > 600;

  // Blocked conditions
  const isClosedDm = !candidate.can_dm;
  const isAlreadyContacted = candidate.already_contacted;
  const isAiFailed = candidate.status === "AI_FAILED";
  const isSparse = Boolean(candidate.insufficient_evidence);
  const isTerminal =
    candidate.status === "SENT" || candidate.status === "REPLIED";

  const isSendDisabled =
    isSending ||
    isClosedDm ||
    isAlreadyContacted ||
    isTerminal ||
    !dmText.trim();

  const handleApproveSend = async () => {
    if (isSendDisabled) return;
    setIsSending(true);
    try {
      await onApproveAndSend(candidate.id, dmText.trim(), dispatchMode);
      onClose();
    } finally {
      setIsSending(false);
    }
  };

  const handleReject = async () => {
    setIsRejecting(true);
    try {
      await onReject(candidate.id);
      onClose();
    } finally {
      setIsRejecting(false);
    }
  };

  const handleRegenerate = async () => {
    setIsRegenerating(true);
    try {
      await onRegenerate(candidate.id);
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleRetry = async () => {
    setIsRetrying(true);
    try {
      await onRetryEvaluation(candidate.id);
    } finally {
      setIsRetrying(false);
    }
  };

  // Parse recent tweets for line-by-line display
  const tweetsList = candidate.recent_tweets
    ? candidate.recent_tweets
        .split("||")
        .map((t) => t.trim())
        .filter(Boolean)
    : [];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="5xl"
      title={t("review_modal.title")}
      subtitle={t("review_modal.subtitle")}
    >
      <ModalBody className="p-0 max-h-[75vh] overflow-y-auto">
        {/* Candidate Summary Header Bar */}
        <div className="bg-muted/40 border-b border-border px-6 py-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-sm">
              {candidate.name.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-foreground text-base">
                  {candidate.name}
                </h3>
                <a
                  href={`https://x.com/${candidate.handle}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline font-mono text-xs flex items-center gap-1"
                >
                  @{candidate.handle}
                  <ExternalLink className="w-3 h-3 opacity-60" />
                </a>
              </div>
              <p className="text-xs text-muted-foreground">
                {candidate.location || t("workspace.default_location")} • {candidate.segment || t("workspace.default_segment")}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <ScorePill score={candidate.fit_score} showIcon size="md" />

            {candidate.can_dm ? (
              <Badge variant="outline" className="border-emerald-300 text-emerald-800 bg-emerald-50">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                {t("ingestion.dm_open")}
              </Badge>
            ) : (
              <Badge variant="outline" className="border-rose-300 text-rose-800 bg-rose-50">
                <Lock className="w-3.5 h-3.5 mr-1 text-rose-600" />
                {t("ingestion.dm_closed")}
              </Badge>
            )}

            <Badge variant="muted" className="font-mono text-xs">
              {candidate.status}
            </Badge>
          </div>
        </div>

        {/* Two-Column Deep Focus Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-border">
          {/* LEFT COLUMN: Grounded Technical Evidence (col-span-6) */}
          <div className="lg:col-span-6 p-6 space-y-5 bg-white">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                {t("review_modal.col_evidence")}
              </h4>
              <Badge variant="outline" className="text-amber-800 border-amber-300 bg-amber-50 text-[11px]">
                <Sparkles className="w-3 h-3 mr-1 text-amber-600" />
                {t("evidence.grounded_badge")}
              </Badge>
            </div>

            {/* AI Fit Assessment */}
            {candidate.fit_reason && (
              <div className="bg-primary/5 rounded-xl p-4 border border-primary/10">
                <div className="text-xs font-bold text-primary mb-1">
                  {t("review_modal.why_fit_label")}
                </div>
                <p className="text-xs text-foreground/90 leading-relaxed">
                  {candidate.fit_reason}
                </p>
              </div>
            )}

            {/* Profile Bio */}
            <div>
              <div className="text-xs font-semibold text-muted-foreground mb-1.5">
                {t("review_modal.bio_label")}
              </div>
              <div className="bg-muted/30 rounded-lg p-3 text-xs text-foreground border border-border/80">
                <EvidenceMark
                  text={candidate.bio}
                  snippet={candidate.evidence_snippet}
                />
              </div>
            </div>

            {/* Verbatim Quote Callout */}
            {candidate.evidence_snippet && (
              <div>
                <div className="text-xs font-semibold text-muted-foreground mb-1.5">
                  {t("review_modal.evidence_quote_label")}
                </div>
                <EvidenceCallout
                  evidenceSnippet={candidate.evidence_snippet}
                />
              </div>
            )}

            {/* Recent Posts & Activity */}
            <div>
              <div className="text-xs font-semibold text-muted-foreground mb-1.5">
                {t("review_modal.tweets_label")}
              </div>
              <div className="space-y-2">
                {tweetsList.length > 0 ? (
                  tweetsList.map((tweet, idx) => (
                    <div
                      key={idx}
                      className="bg-card rounded-lg p-3 text-xs text-foreground/90 border border-border leading-relaxed font-sans"
                    >
                      <EvidenceMark
                        text={tweet}
                        snippet={candidate.evidence_snippet}
                      />
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-muted-foreground italic p-2">
                    {t("review_modal.no_tweets")}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN: Grounded DM Composer & Policy Guards (col-span-6) */}
          <div className="lg:col-span-6 p-6 space-y-5 bg-card/40 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  {t("review_modal.col_composer")}
                </h4>
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span>{t("review_modal.dispatch_mode")}</span>
                  <select
                    data-testid="dispatch-mode-select"
                    value={dispatchMode}
                    onChange={(e) =>
                      setDispatchMode(e.target.value as "SANDBOX" | "LIVE_X")
                    }
                    className="text-xs bg-white border border-border rounded-md px-2 py-1 font-medium text-foreground focus:ring-1 focus:ring-primary outline-hidden"
                  >
                    <option value="SANDBOX">{t("review_modal.mode_sandbox_option")}</option>
                    <option value="LIVE_X">{t("review_modal.mode_live_option")}</option>
                  </select>
                </div>
              </div>

              {/* Guardrail Banners */}
              {isClosedDm && (
                <div className="rounded-xl bg-rose-50 border border-rose-200 p-3.5 flex items-start gap-3">
                  <ShieldAlert className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
                  <div>
                    <div className="text-xs font-bold text-rose-900">
                      {t("review_modal.alert_closed_dm")}
                    </div>
                    <p className="text-[11px] text-rose-700 mt-0.5">
                      {t("review_modal.alert_closed_dm_desc")}
                    </p>
                  </div>
                </div>
              )}

              {isAlreadyContacted && (
                <div className="rounded-xl bg-blue-50 border border-blue-200 p-3.5 flex items-start gap-3">
                  <ShieldCheck className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
                  <div>
                    <div className="text-xs font-bold text-blue-900">
                      {t("review_modal.alert_already_contacted", {
                        handle: candidate.handle,
                        status: candidate.ledger_status || "SENT",
                      })}
                    </div>
                    <p className="text-[11px] text-blue-700 mt-0.5">
                      {t("review_modal.alert_already_contacted_desc")}
                    </p>
                  </div>
                </div>
              )}

              {isAiFailed && (
                <div className="rounded-xl bg-amber-50 border border-amber-200 p-3.5 flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2.5">
                    <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <div className="text-xs font-bold text-amber-900">
                        {t("review_modal.alert_ai_failed")}
                      </div>
                      <p className="text-[11px] text-amber-700 mt-0.5">
                        {candidate.error_message || t("review_modal.service_outage")}
                      </p>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleRetry}
                    loading={isRetrying}
                    data-testid="modal-retry-ai-btn"
                    className="shrink-0 bg-white"
                  >
                    <RotateCw className="w-3.5 h-3.5 mr-1" />
                    {t("actions.retry")}
                  </Button>
                </div>
              )}

              {isSparse && (
                <div className="rounded-xl bg-amber-50 border border-amber-200 p-3 flex items-start gap-2.5">
                  <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <div className="text-xs text-amber-800">
                    {t("review_modal.alert_sparse")}
                  </div>
                </div>
              )}

              {/* Grounded DM Textarea */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <label className="font-semibold text-foreground flex items-center gap-1.5">
                    <MessageSquare className="w-3.5 h-3.5 text-primary" />
                    {t("review_modal.dm_input_label")}
                  </label>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleRegenerate}
                    loading={isRegenerating}
                    disabled={isTerminal || isClosedDm}
                    className="text-xs text-primary hover:text-primary/90 h-6 px-2"
                  >
                    <RotateCw className="w-3 h-3 mr-1" />
                    {t("review_modal.btn_regenerate")}
                  </Button>
                </div>

                <Textarea
                  data-testid="dm-composer-textarea"
                  value={dmText}
                  onChange={(e) => setDmText(e.target.value)}
                  placeholder={t("review_modal.dm_placeholder")}
                  rows={9}
                  className="text-xs font-sans leading-relaxed resize-none bg-white"
                  disabled={isTerminal || isClosedDm}
                />

                {/* Character Counter & Recommendations */}
                <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1">
                  <span
                    className={
                      isOptimal
                        ? "text-emerald-600 font-semibold"
                        : isTooShort
                        ? "text-amber-600 font-medium"
                        : isExceeded
                        ? "text-rose-600 font-bold"
                        : "text-muted-foreground"
                    }
                  >
                    {t("review_modal.char_count", { count: charCount })}
                  </span>
                  <span className="italic">
                    {isOptimal
                      ? t("review_modal.char_recommended")
                      : isTooShort
                      ? t("review_modal.char_too_short")
                      : isExceeded
                      ? t("review_modal.char_too_long")
                      : t("review_modal.char_recommended")}
                  </span>
                </div>
              </div>
            </div>

            {/* Action Bar inside right column */}
            <div className="pt-4 border-t border-border flex items-center justify-between gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={handleReject}
                loading={isRejecting}
                disabled={isTerminal || candidate.status === "REJECTED"}
                data-testid="modal-reject-btn"
                className="text-rose-700 border-rose-200 hover:bg-rose-50"
              >
                <Trash2 className="w-3.5 h-3.5 mr-1" />
                {t("review_modal.btn_reject")}
              </Button>

              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={onClose}>
                  {t("actions.cancel")}
                </Button>

                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleApproveSend}
                  loading={isSending}
                  disabled={isSendDisabled}
                  data-testid="approve-send-btn"
                  className="bg-emerald-600 hover:bg-emerald-700 font-semibold px-4"
                >
                  <Send className="w-3.5 h-3.5 mr-1.5" />
                  {t("review_modal.btn_approve_send")}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </ModalBody>
    </Modal>
  );
};
