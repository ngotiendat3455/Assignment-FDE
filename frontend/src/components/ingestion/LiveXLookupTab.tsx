"use client";

import React, { useState } from "react";
import {
  Search,
  Globe,
  MapPin,
  Lock,
  CheckCircle2,
  ShieldAlert,
  Zap,
  MessageSquare,
} from "lucide-react";
import { Button } from "@/components/atoms/Button";
import { Badge } from "@/components/atoms/Badge";
import { Input } from "@/components/atoms/Input";
import { useToast } from "@/components/molecules/ToastNotification";
import { IngestionAuditCard } from "@/components/ingestion/IngestionAuditCard";
import { lookupLiveXHandle, ingestSingleCandidate } from "@/lib/ingestion-api";
import { LiveXLookupResponse, IngestionAuditReport } from "@/types/ingestion";
import { useI18n } from "@/context/i18n";

const QUICK_HANDLES = ["@minh_quant", "@arjun_infer", "@linhtran_robo"];

export function LiveXLookupTab() {
  const { t } = useI18n();
  const { toast } = useToast();

  const [query, setQuery] = useState<string>("@minh_quant");
  const [lookingUp, setLookingUp] = useState<boolean>(false);
  const [ingesting, setIngesting] = useState<boolean>(false);
  const [profile, setProfile] = useState<LiveXLookupResponse | null>(null);
  const [segment, setSegment] = useState<string>(
    "SEG-02: LLM Inference & AI Infra"
  );
  const [report, setReport] = useState<IngestionAuditReport | null>(null);

  const handleLookup = async (targetHandle?: string) => {
    const raw = (targetHandle ?? query).trim();
    if (!raw) return;
    setLookingUp(true);
    setReport(null);
    try {
      const res = await lookupLiveXHandle(raw);
      setProfile(res);
      setSegment(res.segment);
    } catch {
      toast(t("errors.500_desc"), "error");
    } finally {
      setLookingUp(false);
    }
  };

  const handlePushSingle = async () => {
    if (!profile) return;
    setIngesting(true);
    try {
      const res = await ingestSingleCandidate({
        handle: profile.handle,
        name: profile.name,
        location: profile.location,
        bio: profile.bio,
        recent_tweets: profile.raw_tweets_text,
        can_dm: profile.can_dm,
        segment,
        x_user_id: profile.x_user_id,
      });
      setReport(res);
      toast(t("ingestion.toast_single_success"), "success");
    } catch {
      toast(t("errors.500_desc"), "error");
    } finally {
      setIngesting(false);
    }
  };

  // When ingestion audit report is available, render it as the primary view
  if (report) {
    return (
      <IngestionAuditCard
        report={report}
        onReset={() => {
          setReport(null);
          setProfile(null);
          setQuery("");
        }}
        resetLabel={t("ingestion.btn_reset_live")}
      />
    );
  }

  return (
    <div className="rounded-2xl border border-border bg-white p-6 shadow-xs animate-in fade-in-50 duration-150">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Globe className="h-5 w-5" />
            </div>
            <h2 className="text-lg font-bold text-foreground">
              {t("ingestion.live_title")}
            </h2>
          </div>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            {t("ingestion.live_desc")}
          </p>
        </div>

        <Badge variant={profile?.api_connected ? "positive" : "primary"}>
          {profile?.api_connected
            ? t("ingestion.api_status_live")
            : t("ingestion.api_status_fallback")}
        </Badge>
      </div>

      <div className="mt-5 flex flex-col gap-3 sm:flex-row">
        <div className="flex-1">
          <Input
            icon={Search}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onClear={() => setQuery("")}
            placeholder={t("ingestion.live_input_placeholder")}
            data-testid="live-lookup-input"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleLookup();
              }
            }}
          />
        </div>
        <Button
          variant="primary"
          loading={lookingUp}
          icon={Search}
          onClick={() => handleLookup()}
          data-testid="live-lookup-submit"
        >
          {lookingUp
            ? t("ingestion.btn_looking_up")
            : t("ingestion.btn_lookup")}
        </Button>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span className="font-medium">{t("ingestion.quick_try_label")}</span>
        {QUICK_HANDLES.map((h) => (
          <button
            key={h}
            type="button"
            onClick={() => {
              setQuery(h);
              handleLookup(h);
            }}
            className="rounded-lg border border-border bg-accent px-2.5 py-1 font-mono text-xs font-medium text-primary transition-colors hover:border-primary/40 hover:bg-primary/5"
          >
            {h}
          </button>
        ))}
      </div>

      {profile && (
        <div className="mt-6 rounded-xl border border-border bg-accent p-5">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
            <div>
              <span className="text-[11px] font-bold tracking-wider text-muted-foreground uppercase">
                {t("ingestion.preview_card_title")}
              </span>
              <div className="mt-1 flex flex-wrap items-center gap-2.5">
                <h3 className="text-base font-bold text-foreground">
                  {profile.name}
                </h3>
                <span className="font-mono text-sm font-semibold text-primary">
                  @{profile.handle}
                </span>
                <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                  <MapPin className="h-3.5 w-3.5" />
                  {profile.location}
                </span>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {profile.can_dm ? (
                <Badge variant="positive" icon={CheckCircle2}>
                  {t("ingestion.dm_open")}
                </Badge>
              ) : (
                <Badge variant="warning" icon={Lock}>
                  {t("ingestion.dm_closed")}
                </Badge>
              )}

              {profile.already_contacted && (
                <Badge variant="destructive" icon={ShieldAlert}>
                  {t("ingestion.already_contacted_warn")} (
                  {profile.existing_ledger_status})
                </Badge>
              )}
            </div>
          </div>

          <div className="mt-4 space-y-4">
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase">
                {t("ingestion.bio_label")}
              </p>
              <p className="mt-1 rounded-lg border border-border bg-white p-3 text-sm text-foreground">
                {profile.bio}
              </p>
            </div>

            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase">
                {t("evidence.recent_tweets")}
              </p>
              <div className="mt-1.5 space-y-2">
                {profile.recent_tweets.map((tweet, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-2.5 rounded-lg border border-border bg-white p-3 text-xs text-foreground"
                  >
                    <MessageSquare className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                    <span>{tweet}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-5 flex flex-col gap-4 border-t border-border pt-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="w-full max-w-md">
              <label
                htmlFor="live-segment-select"
                className="mb-1.5 block text-xs font-semibold text-foreground"
              >
                {t("ingestion.segment_label")}
              </label>
              <select
                id="live-segment-select"
                value={segment}
                onChange={(e) => setSegment(e.target.value)}
                className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-foreground focus:border-primary focus:ring-2 focus:ring-primary focus:outline-none"
              >
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
              loading={ingesting}
              disabled={profile.already_contacted}
              icon={Zap}
              onClick={handlePushSingle}
              data-testid="live-ingest-btn"
            >
              {t("ingestion.btn_push_single")}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
