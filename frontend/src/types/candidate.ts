export type CandidateStatus =
  | "QUEUED_FOR_AI"
  | "PENDING_REVIEW"
  | "INSUFFICIENT_EVIDENCE"
  | "AI_FAILED"
  | "REJECTED"
  | "APPROVED_QUEUED"
  | "SENT"
  | "SEND_BLOCKED"
  | "REPLIED";

export interface CandidateItem {
  id: number;
  x_user_id?: string | null;
  handle: string;
  name: string;
  location?: string | null;
  bio: string;
  recent_tweets: string;
  can_dm: boolean;
  segment?: string | null;
  is_match?: boolean | null;
  fit_score?: number | null;
  fit_reason?: string | null;
  evidence_snippet?: string | null;
  draft_dm?: string | null;
  edited_dm?: string | null;
  insufficient_evidence?: boolean;
  status: CandidateStatus;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;

  // Enriched Ledger Fields
  already_contacted: boolean;
  ledger_status?: string | null;
  needs_attention: boolean;
  sent_message?: string | null;
  reply_text?: string | null;
  sent_at?: string | null;
  replied_at?: string | null;
}

export interface CandidateListResponse {
  total: number;
  items: CandidateItem[];
}

export interface StateMachineSummary {
  QUEUED_FOR_AI: number;
  PENDING_REVIEW: number;
  INSUFFICIENT_EVIDENCE: number;
  AI_FAILED: number;
  REJECTED: number;
  APPROVED_QUEUED: number;
  SEND_BLOCKED: number;
  SENT: number;
  REPLIED: number;
  total_in_ledger: number;
  needs_attention_count: number;
}

export interface SendCandidatePayload {
  custom_message?: string | null;
  idempotency_key?: string | null;
  dispatch_mode?: string;
}

export interface SendCandidateResponse {
  candidate: CandidateItem;
  ledger: {
    id: number;
    candidate_id: number;
    handle: string;
    idempotency_key: string;
    sent_message: string;
    dispatch_mode: string;
    external_dm_id?: string | null;
    status: string;
    needs_attention: boolean;
    sent_at?: string | null;
  };
}

