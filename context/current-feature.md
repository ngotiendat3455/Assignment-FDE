# Current Active Feature: Feature 06 – Outreach Ledger, Inbox Tracker & Calibration Matrix
*(Sprint Status & Active Tracking)*

---

## 1. Active Feature Info
- **Active Task:** WBS Task 6 (Immutable Outreach Ledger, Founder Reply Simulator/Tracker, Conversation Audit Drawer & Partner Calibration Matrix): [`06-outreach-ledger-and-dashboard.md`](file:///d:/AssignmentFDE/context/features/06-outreach-ledger-and-dashboard.md)
  - ✅ **Sub-task 6.1 (Backend Ledger & Calibration Service & Router – `backend/app/services/ledger_service.py` & `backend/app/api/ledger.py`):** Implemented `GET /api/ledger` (with `filter_tab`, `search`, KPI summary metrics, and auto-seeding of `OUT-101`..`OUT-104` baseline), `POST /api/ledger/{id}/reply` (simulate/record founder reply -> `REPLIED` + `needs_attention=True`), `POST /api/ledger/{id}/handled` (resolve attention flag -> `needs_attention=False`), and `GET /api/ledger/calibration` (benchmarking AI Scorer against `candidates_seed.csv` & `fund_reference_scores.csv`).
  - ✅ **Sub-task 6.2 (Automated Pytest Suite – `backend/tests/test_ledger_and_calibration.py`):** Wrote 4 comprehensive tests covering `OUT-101`..`OUT-104` seed history baseline, filter pills (`needs_attention`, `sent`, `blocked`), founder reply simulation -> `needs_attention=True`, mark handled -> `needs_attention=False`, closed DM reply rejection (`422`), and calibration matrix accuracy (`100%` across 19 unique profiles) -> **29/29 total backend tests PASSED**.
  - ✅ **Sub-task 6.3 (Frontend Ledger & Calibration Types, Client API & Symmetrical i18n – `frontend/src/types/ledger.ts`, `frontend/src/lib/ledger-api.ts`, `en.json`, `vi.json`):** Defined strict TypeScript contracts (`no-explicit-any`), zero-fake-fallback API client functions (`fetchLedgerEntries`, `recordLedgerReply`, `markLedgerHandled`, `fetchCalibrationMatrix`), and 100% symmetrical English/Vietnamese translation keys under `ledger.*` and `calibration.*`.
  - ✅ **Sub-task 6.4 (Frontend Outreach Ledger, Record Reply Modal, Audit Drawer & Calibration Matrix Pages – `frontend/src/components/ledger/LedgerDashboardClient.tsx`, `frontend/src/app/ledger/page.tsx`, `frontend/src/app/calibration/page.tsx`, `frontend/src/app/dashboard/page.tsx`):** Built Tab 1 (Outreach Ledger & Inbox with 4 KPI StatCards, Filter Pills, Search, Record Reply Modal, and Conversation Detail & Immutable Audit Trail Drawer) and Tab 2 (Partner Calibration Matrix comparing AI scores against Fund Reference scores).
  - ✅ **Sub-task 6.5 (End-to-End Verification & Sprint Log Finalization):** Verified `python -m pytest backend/tests/ -v` (**29/29 PASSED**) and `npm run build` in `frontend/`.
- **Completed Foundation Tasks:**
  - ✅ **Task 0:** [`00-base-layout-design-system.md`](file:///d:/AssignmentFDE/context/features/00-base-layout-design-system.md) (Atomic Design System, Pure Tailwind v4 `@theme`, English-First i18n, Paginated Table & AppShell)
  - ✅ **Task 1:** [`01-data-pack-and-ingestion.md`](file:///d:/AssignmentFDE/context/features/01-data-pack-and-ingestion.md) (Full-Stack Triple-Tab Ingestion Hub, Pre-flight CSV Check, Live X Lookup & 3-Tier Deduplication)
  - ✅ **Task 2:** [`02-database-and-state-machine.md`](file:///d:/AssignmentFDE/context/features/02-database-and-state-machine.md) (SQLite WAL Schema, 9-State Lifecycle Machine, Two-Tier Zero Double-Messaging Gate & Candidate Lifecycle API)
  - ✅ **Task 3:** [`03-auth-and-security.md`](file:///d:/AssignmentFDE/context/features/03-auth-and-security.md) (Next.js BFF HttpOnly Cookie Auth, 7-Day JWT, Pre-filled Partner Login, Protected FastAPI Middleware & Error Pages)
  - ✅ **Task 4:** [`04-dual-queue-and-ai-send-engine.md`](file:///d:/AssignmentFDE/context/features/04-dual-queue-and-ai-send-engine.md) (SQLite Dual Queue Worker, Tri-Guard AI Evaluator, Token Bucket Limiter & Dual-Mode Safe Send Dispatcher)
  - ✅ **Task 5:** [`05-hitl-review-and-composer-ui.md`](file:///d:/AssignmentFDE/context/features/05-hitl-review-and-composer-ui.md) (Table-First Review Workspace, Search/Filter Triage, Grounded Evidence Highlighting & Review/Composer Modal)
  - ✅ **Task 6:** [`06-outreach-ledger-and-dashboard.md`](file:///d:/AssignmentFDE/context/features/06-outreach-ledger-and-dashboard.md) (Immutable Outreach Ledger, Founder Reply Simulator/Tracker, Audit Trail Drawer & Partner Calibration Matrix)
- **Next Spec Reference:** [`07-testing-and-deployment.md`](file:///d:/AssignmentFDE/context/features/07-testing-and-deployment.md)
- **Current Status:** `COMPLETED (Feature 06)`

---

## 2. Completed Milestones
1. ✅ **Repository & Context Foundation:** Initialized structured context, specifications, and WBS execution plan.
2. ✅ **Database Models (`backend/app/models/`):**
   - `User`: Account management & partner roles.
   - `Candidate`: 9-state lifecycle with profile context & AI draft fields.
   - `OutreachLedger`: Strict 1-to-1 unique foreign key preventing duplicate dispatch.
   - `JobQueue`: Persistent asynchronous task queue for AI evaluation and DM sending.
3. ✅ **Ingestion Engine (`backend/app/services/ingestion.py`):**
   - Silent handle normalizer (lowercase, trim whitespace, strip `@`).
   - In-batch deduplication (merging duplicates like `P002` & `P020`).
   - Historical ledger cross-checking against previous outreach log.
4. ✅ **Bootstrap Seeding Script (`backend/seed_data.py`):**
   - Auto-creates default Partner user (`partner@genaifund.ai`).
   - Seeds 20 realistic candidate profiles from `candidates_seed.csv`.
   - Seeds 4 historical ledger records (`OUT-101` to `OUT-104`).
5. ✅ **Automated Pytest Suite (`backend/tests/test_ingestion.py`):**
   - 5/5 test cases PASSED (verifying idempotency, handle sanitization, duplicate protection).
6. ✅ **Frontend Design System Implementation (`frontend/`):**
   - Initialized Next.js 15 App Router project structure with TypeScript and Tailwind CSS.
   - Design tokens configured in CSS (`--color-primary`, `--color-destructive`, etc.) matching Venture Capital theme.
   - Built full Atomic Design System:
     - **Atoms:** `Button`, `Badge` (with `urgent` pulse), `ScorePill` (0..4), `Input`, `Textarea` (with live counter), `EvidenceMark` (amber `<mark>`).
     - **Molecules:** `Tabs` (`LineTabs`, `PillTabs`), `TablePagination` (10/25/50 selector), `StatCard`, `InlineComposer`, `EvidenceCallout`, `FileDropzone`, `ToastNotification`.
     - **Organisms:** `AppSidebar` (collapsible w-64 vs w-16), `TopHeader`, `DataTable` compound, `Modal`, `Drawer`, `ErrorViews` (401, 403, 500), `GlobalErrorBoundary`.
     - **Layout:** `AppProviders`, `BreakpointLayout`, `AppShell`.
     - **i18n:** Bilingual English/Vietnamese dictionary with instant in-memory toggle.
   - Verified via `npm run build` -> **Compiled successfully (5/5 static pages) with 0 errors**.
7. ✅ **Strict i18n Architecture & English-First Rules:**
   - Established English (`en`) as the primary/default language across all components (standard for international VC & evaluation).
   - Removed 100% of hardcoded Vietnamese and mixed bilingual strings from templates; all user-facing copy is now routed through `useI18n().t()`.
   - Created symmetrical translation dictionaries in `locales/en.json` and `locales/vi.json`.
   - Updated Rule in [`00-base-layout-design-system.md`](file:///d:/AssignmentFDE/context/features/00-base-layout-design-system.md#L200-L225).
8. ✅ **Strict Coding Standards & Pure Tailwind CSS v4 Adoption:**
   - Documented full coding standards in [`context/coding-standards.md`](file:///d:/AssignmentFDE/context/coding-standards.md).
   - Upgraded `frontend/` to pure **Tailwind CSS v4** (`@tailwindcss/postcss: ^4.3.5`, `tailwindcss: ^4.3.5`).
   - Completely removed legacy `tailwind.config.ts`; all theme variables and styling rules are 100% CSS-driven via `@theme` in `src/app/globals.css`.
   - Verified via `npm run build` -> **Compiled successfully (5/5 static pages) with 0 errors**.
9. ✅ **Full-Stack Implementation of Feature 01 (`01-data-pack-and-ingestion.md`):**
   - **Backend Ingestion Service (`backend/app/services/ingestion.py`):**
     - Upgraded `normalize_handle` to strip `@`, quotes, whitespace, and extract usernames from full `https://x.com/...` or `https://twitter.com/...` URLs.
     - Implemented `preflight_csv_check` for non-destructive CSV validation and 5-row preview generation.
     - Implemented `ingest_seed_pack` (1-Click 20 SEA profile loader with 3-tier deduplication: 16 queued for AI, 1 in-batch duplicate `@minh_quant` merged, 3 past sent/replied ledger collisions `@linhtran_robo`, `@putri_agentic`, `@harith_medai` protected).
     - Implemented `lookup_x_handle` supporting Live X API v2 (`X_BEARER_TOKEN`) with automatic fallback to SQLite/Seed Pack/Synthetic preview.
   - **FastAPI Endpoints (`backend/app/api/ingestion.py` & `backend/app/main.py`):**
     - `POST /api/ingestion/seed`, `POST /api/ingestion/preflight`, `POST /api/ingestion/csv`, `GET /api/ingestion/x-lookup`, `POST /api/ingestion/single`, and `GET /api/ingestion/template`.
   - **Automated Pytest Suite (`backend/tests/test_ingestion.py`):**
     - Expanded to 9 unit & FastAPI integration tests -> **9/9 PASSED**.
   - **Frontend Triple-Tab Ingestion Hub (`frontend/src/app/ingestion/page.tsx` & `frontend/src/components/ingestion/`):**
     - Built `SeedPackTab.tsx` (Wireframe 1), `CsvUploadTab.tsx` (Wireframe 2), `LiveXLookupTab.tsx` (Wireframe 3), and `IngestionAuditCard.tsx`.
     - **UX Refinement:** Chuyển `IngestionAuditCard` thành Primary View nổi bật ngay vị trí chính khi thực hiện nạp dữ liệu xong (thay vì chèn xuống cuối), tích hợp nút `[↺ Quay lại Biểu mẫu / Nạp tiếp]` và `[🚀 Chuyển tới Bàn duyệt HITL]`.
     - Added full symmetrical English/Vietnamese i18n dictionary under `ingestion.*` in `en.json` and `vi.json`.
     - Verified via `npm run build` -> **Compiled successfully (6/6 static pages including `/ingestion`) with 0 errors**.
10. ✅ **Full Implementation of Feature 02 (`02-database-and-state-machine.md`):**
    - **9-State Lifecycle Machine (`backend/app/services/state_machine.py`):**
      - Implemented formal `ALLOWED_TRANSITIONS` matrix across all 9 states (`QUEUED_FOR_AI`, `PENDING_REVIEW`, `INSUFFICIENT_EVIDENCE`, `AI_FAILED`, `REJECTED`, `APPROVED_QUEUED`, `SEND_BLOCKED`, `SENT`, `REPLIED`).
      - Prevented terminal outreach states (`SENT`, `REPLIED`) from ever regressing to pre-send states.
    - **Two-Tier Idempotency & Zero Double-Messaging Gate (`approve_and_send_candidate`):**
      - *Tier 1 (Application Guard):* Verifies candidate status, existing `outreach_ledger` entries (`candidate_id` or `handle`), and `idempotency_key` before dispatch -> returns `409 Conflict` on duplicate attempts.
      - *Closed DM Guard:* Automatically transitions `can_dm = False` profiles (`@arjun_infer`) to `SEND_BLOCKED` (`422 Unprocessable Entity`) and records a `BLOCKED` ledger entry.
      - *Tier 2 (Database Unique Constraint + Atomic Transaction):* Catches `sqlalchemy.exc.IntegrityError` on concurrent double-clicks and rolls back cleanly with `409 Conflict`.
    - **Candidate Lifecycle REST API (`backend/app/api/candidates.py`):**
      - Implemented `GET /api/candidates`, `GET /api/candidates/state-summary`, `GET /api/candidates/{id}`, `POST /api/candidates/{id}/send`, `POST /api/candidates/{id}/reject`, `POST /api/candidates/{id}/retry`, `POST /api/candidates/{id}/reply`, and `POST /api/candidates/{id}/handled`.
    - **Automated Pytest Suite (`backend/tests/test_state_machine.py`):**
      - Added 5 comprehensive tests covering double-click idempotency (`409 Conflict`), seed history protection (`@linhtran_robo`), closed DM protection (`@arjun_infer`), 9-state lifecycle transitions + reply/handled workflow, and file-backed SQLite WAL persistence across server restarts -> **14/14 total tests PASSED**.
11. ✅ **Full-Stack Implementation of Feature 03 (`03-auth-and-security.md`):**
    - **Backend Security Core & `get_current_user` Guard (`backend/app/core/security.py` & `backend/app/core/config.py`):**
      - Configured 7-day JWT session lifetime (`ACCESS_TOKEN_EXPIRE_MINUTES = 10080`).
      - Implemented `ensure_default_partner_user` to guarantee the pre-filled Partner account (`partner@genaifund.ai` / `GenAIFund2026!`) always exists in SQLite.
      - Built `get_current_user` FastAPI dependency supporting both `Authorization: Bearer <jwt>` header and `session_token` HttpOnly cookie, rejecting unauthenticated/expired requests with `401 Unauthorized`.
    - **FastAPI Auth Router (`backend/app/api/auth.py`):**
      - Implemented `POST /api/auth/login`, `POST /api/auth/demo-login`, `POST /api/auth/register`, `GET /api/auth/me`, and `POST /api/auth/logout`.
      - Protected `/api/candidates` router with `Depends(get_current_user)`.
    - **Next.js BFF Route Handlers, Private Route Middleware & Error Pages (`frontend/src/`):**
      - Built `POST /api/auth/login` and `POST /api/auth/logout` Next.js BFF route handlers managing the 7-day `HttpOnly` `session_token` cookie (`SameSite=Lax`).
      - Built [`frontend/src/middleware.ts`](file:///d:/AssignmentFDE/frontend/src/middleware.ts) enforcing private route protection on all workspace pages (`/`, `/ingestion`, `/workspace`, `/ledger`, `/calibration`), checking JWT expiration (`exp`), redirecting unauthenticated sessions to `/login?from=...`, and enforcing Partner role RBAC (`/403` for unauthorized roles).
      - Built `/login` page ([`login/page.tsx`](file:///d:/AssignmentFDE/frontend/src/app/login/page.tsx)) with pre-filled `partner@genaifund.ai` & `GenAIFund2026!`, show/hide password toggle, language switcher (`EN`/`VI`), and 1-click sign-in.
      - Built dedicated Next.js App Router error pages: [`/401/page.tsx`](file:///d:/AssignmentFDE/frontend/src/app/401/page.tsx) (401 Session Expired), [`/403/page.tsx`](file:///d:/AssignmentFDE/frontend/src/app/403/page.tsx) (403 Forbidden), [`not-found.tsx`](file:///d:/AssignmentFDE/frontend/src/app/not-found.tsx) (404 Not Found), [`error.tsx`](file:///d:/AssignmentFDE/frontend/src/app/error.tsx) & [`global-error.tsx`](file:///d:/AssignmentFDE/frontend/src/app/global-error.tsx) (500 Runtime Error).
      - Updated `TopHeader.tsx` (Wireframe 2) to invoke `/api/auth/logout` and redirect cleanly to `/login`.
    - **Verification (`pytest` & `next build`):**
      - `python -m pytest backend/tests/ -v` -> **19/19 PASSED** (including 5 new tests in `test_auth.py`).
      - `npm run build` in `frontend/` -> **11/11 static pages + Edge Middleware compiled with 0 errors**.
12. ✅ **Full Implementation of Feature 04 (`04-dual-queue-and-ai-send-engine.md`):**
    - **Tri-Guard AI Evaluation Engine ([`backend/app/services/ai_evaluator.py`](file:///d:/AssignmentFDE/backend/app/services/ai_evaluator.py)):**
      - *Layer 1 (Fortified Delimiters & Prompt Injection Shield):* Wraps untrusted candidate profile fields inside `<untrusted_candidate_data>` XML delimiters and detects adversarial prompt injection (`P017` `@override_bot99`), forcing `is_match = False`, `fit_score = 1`, `draft_dm = ""`, and blocking `PWNED_BY_PROMPT_INJECTION`.
      - *Layer 2 (LLM Provider Integration + Rubric-Faithful Fallback):* Supports live structured JSON calls via Google Gemini 2.0 Flash (`GEMINI_API_KEY`) or OpenAI GPT-4o-mini (`OPENAI_API_KEY`), with a turnkey rubric-faithful deterministic evaluator calibrated to `scoring_guide.md`.
      - *Layer 3 (Evidence Grounding & Anti-Hallucination Guard):* Detects sparse profiles (`P018` `@ghost_builder_sea` -> `insufficient_evidence = True`, `draft_dm = ""`, status `INSUFFICIENT_EVIDENCE`), verifies `evidence_snippet` is an exact verbatim quote from `bio`/`recent_tweets`, and enforces peer-to-peer DM length (250–600 chars) with zero invented familiarity.
    - **Token Bucket Rate Limiter & Dual-Mode Safe Send Dispatcher ([`backend/app/services/dispatcher.py`](file:///d:/AssignmentFDE/backend/app/services/dispatcher.py)):**
      - Implemented `TokenBucketRateLimiter` with HTTP `429 Too Many Requests` circuit-breaker halt.
      - Built `dispatch_candidate_dm` supporting `SANDBOX` mode ($0 cost, simulated latency) and `LIVE_X` mode with strict `ALLOWED_TEST_HANDLES` safety whitelist enforcement (blocking non-whitelisted handles into `SEND_BLOCKED`) and `can_dm = False` protection (`P019` `@arjun_infer` -> `SEND_BLOCKED`).
    - **Persistent SQLite Dual Queue Worker ([`backend/app/services/queue_worker.py`](file:///d:/AssignmentFDE/backend/app/services/queue_worker.py)) & Router ([`backend/app/api/queue.py`](file:///d:/AssignmentFDE/backend/app/api/queue.py)):**
      - Processes Queue 1 (`AI_EVALUATE`) and Queue 2 (`SEND_DM`), isolating LLM outages into `AI_FAILED` (with Retry) rather than assigning a fake low score.
      - Wired `BackgroundTasks` into `/api/ingestion/seed`, `/api/ingestion/csv`, and `/api/ingestion/single` so newly ingested profiles are automatically evaluated in the background.
      - Added `GET /api/queue/status`, `POST /api/queue/process`, `POST /api/queue/evaluate/{candidate_id}`, and `POST /api/queue/dispatch/{candidate_id}`.
    - **Verification (`pytest`):**
      - Created [`backend/tests/test_dual_queue_and_ai.py`](file:///d:/AssignmentFDE/backend/tests/test_dual_queue_and_ai.py) -> **6/6 PASSED (`25/25` total backend tests PASSED)**.
13. ✅ **Full Implementation of Feature 05 (`05-hitl-review-and-composer-ui.md`):**
    - **Candidates Client API & Types ([`frontend/src/types/candidate.ts`](file:///d:/AssignmentFDE/frontend/src/types/candidate.ts) & [`frontend/src/lib/candidates-api.ts`](file:///d:/AssignmentFDE/frontend/src/lib/candidates-api.ts)):**
      - Typed interfaces for candidate records, 9 lifecycle states, and state summary metrics.
      - Client methods (`fetchCandidates`, `fetchCandidateDetail`, `fetchStateMachineSummary`, `sendCandidateDm`, `rejectCandidate`, `retryCandidateEvaluation`, `regenerateAiEvaluation`) handling authentication, errors, and redirects.
    - **Table-First Review Workspace Canvas ([`frontend/src/app/page.tsx`](file:///d:/AssignmentFDE/frontend/src/app/page.tsx)):**
      - Built full-width Table canvas with search-as-you-type, multi-tab triage pills (All, Matches 3-4, Pending Review, Sparse, Closed DMs/Blocked, Sent/Replied, Rejected), real-time KPI stat cards, and table pagination (10/25/50).
      - Fast table actions: `[👁️ Review & Approve]`, `[🗑️ Quick Reject]`, `[🔄 Retry AI]`, and `CRM` audit drawer for replied candidates.
    - **Dedicated Review & Grounded Composer Modal ([`frontend/src/components/organisms/ReviewComposerModal.tsx`](file:///d:/AssignmentFDE/frontend/src/components/organisms/ReviewComposerModal.tsx)):**
      - Two-column deep focus view: Left column renders grounded evidence with amber `<EvidenceMark>` verbatim highlighting and quote callout; Right column renders live DM editor with live character counter (250-600 chars), closed DM guard, sparse profile guard, double-messaging lock, and actions (`[🔄 Regenerate with AI]`, `[🗑️ Reject]`, `[⚡ Approve & Send DM]`).
    - **Verification:**
      - `python -m pytest backend/tests/ -v` -> **25/25 PASSED**.
      - `npm run build` in `frontend/` -> **11/11 static pages + Edge Middleware compiled with 0 errors**.
14. ✅ **Full-Stack Implementation of Feature 06 (`06-outreach-ledger-and-dashboard.md`):**
    - **Backend Ledger & Calibration Service & Router ([`backend/app/services/ledger_service.py`](file:///d:/AssignmentFDE/backend/app/services/ledger_service.py) & [`backend/app/api/ledger.py`](file:///d:/AssignmentFDE/backend/app/api/ledger.py)):**
      - Implemented `GET /api/ledger` returning `OUT-101`..`OUT-104` baseline + newly dispatched DMs, filter pill counts (`all`, `needs_attention`, `replied`, `sent`, `blocked`), search query matching, and KPI summary metrics (`dispatched_count`, `replied_count`, `reply_rate`, `needs_attention_count`, `total_safety_interceptions`).
      - Implemented `POST /api/ledger/{id}/reply` to record/simulate founder replies (`status = REPLIED`, `needs_attention = True`, rejecting `BLOCKED` DMs with `422`).
      - Implemented `POST /api/ledger/{id}/handled` to resolve urgent attention flags (`needs_attention = False`).
      - Implemented `GET /api/ledger/calibration` benchmarking the Tri-Guard AI Evaluator against `candidates_seed.csv` & `fund_reference_scores.csv` (`100%` alignment accuracy across 19 unique profiles, `2/2` prompt injection & sparse traps neutralized, `0.00` mean score delta).
    - **Automated Pytest Suite ([`backend/tests/test_ledger_and_calibration.py`](file:///d:/AssignmentFDE/backend/tests/test_ledger_and_calibration.py)):**
      - Added 4 comprehensive tests covering seed history baseline, filter pills, founder reply simulation, mark handled, closed DM guard, and calibration matrix accuracy -> **29/29 total backend tests PASSED**.
    - **Frontend Outreach Ledger, Reply Simulator Modal, Audit Drawer & Calibration Matrix ([`frontend/src/components/ledger/LedgerDashboardClient.tsx`](file:///d:/AssignmentFDE/frontend/src/components/ledger/LedgerDashboardClient.tsx), [`/ledger`](file:///d:/AssignmentFDE/frontend/src/app/ledger/page.tsx), [`/calibration`](file:///d:/AssignmentFDE/frontend/src/app/calibration/page.tsx), [`/dashboard`](file:///d:/AssignmentFDE/frontend/src/app/dashboard/page.tsx)):**
      - Built Tab 1 (Outreach Ledger & Inbox with 4 KPI StatCards, Filter Pills, Search, Record Reply Modal with 1-click sample reply, and Conversation Detail & Immutable Audit Trail Drawer).
      - Built Tab 2 (Partner Calibration Matrix comparing AI scores vs. Fund Reference scores across `P001`..`P020`).
      - Added 100% symmetrical English & Vietnamese translations under `ledger.*` and `calibration.*` in `en.json` and `vi.json`.

---

## 3. Next Immediate Steps (Feature 07: E2E Testing & Turnkey Deployment)
1. **Implement Feature 07 (`07-testing-and-deployment.md`):**
   - Finalize end-to-end verification, turnkey startup scripts, and deployment readiness.
