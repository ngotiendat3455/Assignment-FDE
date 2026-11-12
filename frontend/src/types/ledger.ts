export type LedgerFilterTab = "all" | "needs_attention" | "replied" | "sent" | "blocked";

export type LedgerStatus = "SENT" | "REPLIED" | "BLOCKED";

export interface LedgerEntryItem {
  id: number;
  outreach_id: string;
  candidate_id: number;
  handle: string;
  candidate_name: string;
  candidate_location: string;
  candidate_segment: string;
  candidate_bio: string;
  candidate_fit_score: number | null;
  can_dm: boolean;
  idempotency_key: string;
  sent_message: string;
  dispatch_mode: "SANDBOX" | "LIVE_X" | string;
  external_dm_id: string;
  sent_by_user_id: number | null;
  sent_at: string | null;
  replied_at: string | null;
  reply_text: string | null;
  needs_attention: boolean;
  status: LedgerStatus;
}

export interface LedgerKpiMetrics {
  dispatched_count: number;
  replied_count: number;
  reply_rate: number;
  needs_attention_count: number;
  blocked_dm_count: number;
  dedup_collisions_prevented: number;
  in_batch_duplicates_merged: number;
  total_safety_interceptions: number;
}

export interface LedgerFilterCounts {
  all: number;
  needs_attention: number;
  replied: number;
  sent: number;
  blocked: number;
}

export interface LedgerListResponse {
  total: number;
  kpi: LedgerKpiMetrics;
  counts: LedgerFilterCounts;
  items: LedgerEntryItem[];
}

export type CalibrationBadgeCode =
  | "EXACT_MATCH"
  | "CLOSE_MATCH"
  | "MISMATCH"
  | "INJECTION_BLOCKED"
  | "SPARSE_FLAGGED"
  | "CLOSED_DM_CAUGHT"
  | "DUPLICATE_MERGED";

export interface CalibrationRowItem {
  profile_id: string;
  handle: string;
  name: string;
  location: string;
  segment: string;
  case_type: string;
  scored_by: string;
  ai_score: number;
  reference_score: number;
  ai_is_match: boolean;
  reference_is_match: boolean;
  score_delta: number;
  is_aligned: boolean;
  badge_code: CalibrationBadgeCode;
  ai_reason: string;
  partner_note: string;
  can_dm: boolean;
}

export interface CalibrationKpiMetrics {
  alignment_accuracy: number;
  unique_benchmarked: number;
  aligned_count: number;
  total_seed_rows: number;
  duplicate_rows_detected: number;
  safety_blocks_verified: number;
  safety_blocks_total: number;
  mean_score_delta: number;
}

export interface CalibrationMatrixResponse {
  kpi: CalibrationKpiMetrics;
  items: CalibrationRowItem[];
}

