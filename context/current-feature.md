# Current Active Feature: Feature 07 – Live Verification, Clean User-Only Reset, Docker & AWS Multi-Env Deployment
*(Sprint Status & Active Tracking)*

---

## 1. Active Feature Info
- **Active Task:** WBS Task 7 (Rebuilt Production Readiness & Deployment Spec): [`07-verification-and-handover.md`](file:///d:/AssignmentFDE/context/features/07-verification-and-handover.md)
  - ✅ **Sub-task 7.1 (Clean User-Only DB Reset):**
    - Created [`backend/reset_clean_users.py`](file:///d:/AssignmentFDE/backend/reset_clean_users.py) wiping `job_queue`, `outreach_ledger`, `candidates` (and resetting `sqlite_sequence`) while keeping `users` (`partner@xscout.local`, optional `--with-analyst`, `--purge-extra-users`, `--db-url`, `--yes`). Executed on `outreach.db` (`Users: 1`, `Candidates: 0`, `OutreachLedger: 0`, `JobQueue: 0`).
  - ✅ **Sub-task 7.2 (Live X & Live AI Verification Suite + `LIVE_X` Real Client):**
    - Built [`backend/app/services/x_client.py`](file:///d:/AssignmentFDE/backend/app/services/x_client.py) (RFC 5849 OAuth 1.0a HMAC-SHA1 header signing, `resolve_x_user_id`, `send_x_dm` via X API v2 `/2/dm_conversations/with/{id}/messages`, `XApiRateLimitError`), wired into [`state_machine.py`](file:///d:/AssignmentFDE/backend/app/services/state_machine.py), [`candidates.py`](file:///d:/AssignmentFDE/backend/app/api/candidates.py), [`config.py`](file:///d:/AssignmentFDE/backend/app/core/config.py) (`LIVE_X_DRY_RUN`), and [`backend/.env.example`](file:///d:/AssignmentFDE/backend/.env.example).
    - Built [`backend/scripts/verify_live_keys.py`](file:///d:/AssignmentFDE/backend/scripts/verify_live_keys.py) covering Gate **L1** (Live Gemini/OpenAI + Tri-Guard + `--full-benchmark`), **L2** (`X_BEARER_TOKEN` live lookup), and **L3** (`LIVE_X` whitelist & OAuth check). Current `backend/.env` has no live keys configured yet (`SKIPPED_NO_KEY`).
    - Added 4 hermetic tests in [`backend/tests/test_verification_tools.py`](file:///d:/AssignmentFDE/backend/tests/test_verification_tools.py).
  - ✅ **Sub-task 7.3 (Docker Packaging & Docker Compose):**
    - Added [`frontend/next.config.ts`](file:///d:/AssignmentFDE/frontend/next.config.ts) (`output: "standalone"`), [`frontend/src/lib/api-config.ts`](file:///d:/AssignmentFDE/frontend/src/lib/api-config.ts) (`NEXT_PUBLIC_API_BASE_URL=auto`), [`frontend/src/app/healthz/route.ts`](file:///d:/AssignmentFDE/frontend/src/app/healthz/route.ts), fixed HTTPS/HTTP cookie cleanup in [`logout/route.ts`](file:///d:/AssignmentFDE/frontend/src/app/api/auth/logout/route.ts), and updated client API fetchers.
    - Authored [`backend/Dockerfile`](file:///d:/AssignmentFDE/backend/Dockerfile), [`frontend/Dockerfile`](file:///d:/AssignmentFDE/frontend/Dockerfile), [`.dockerignore`](file:///d:/AssignmentFDE/.dockerignore), [`frontend/.dockerignore`](file:///d:/AssignmentFDE/frontend/.dockerignore), [`.env.docker.example`](file:///d:/AssignmentFDE/.env.docker.example), [`infra/nginx/nginx.conf`](file:///d:/AssignmentFDE/infra/nginx/nginx.conf), and [`docker-compose.yml`](file:///d:/AssignmentFDE/docker-compose.yml) (`x-simulator`, `backend` with `/app/data` named volume, `frontend`, optional `--profile prod-sim` Nginx proxy). Verified `docker compose config --quiet` (live `docker compose up --build -d` awaits Docker Desktop daemon start).
  - ✅ **Sub-task 7.4 (Manual QA Checklist & UI/Copy Pre-checks):**
    - Created [`tests/manual/MANUAL_QA_CHECKLIST.md`](file:///d:/AssignmentFDE/tests/manual/MANUAL_QA_CHECKLIST.md) covering Groups A–F (`MQ-A1`..`MQ-F2`), verified `MQ-A1` clean reset + automated suite after UI/copy polish (login card cleanup, collapsible KPI metrics, single-line `ScorePill`, simplified product labels & table headers).
  - ✅ **Sub-task 7.5 (AWS Terraform Multi-Env IaC `dev`/`staging`/`prod` ↔ 3 `RUNTIME_PROFILE` + CI/CD):**
    - Built [`infra/terraform/`](file:///d:/AssignmentFDE/infra/terraform/) (`versions.tf`, `backend.tf.example`, `main.tf`, `variables.tf`, `outputs.tf`, modules `network/`, `alb/`, `storage_secrets/`, `ecs_cluster/`, and [`environments/{dev,staging,prod}.tfvars`](file:///d:/AssignmentFDE/infra/terraform/environments/dev.tfvars) mapped 1-1 to `OFFLINE_MOCK` / `HYBRID_AUTO` / `LIVE_PRODUCTION`), plus [`.github/workflows/ci-cd.yml`](file:///d:/AssignmentFDE/.github/workflows/ci-cd.yml) and [`infra/README.md`](file:///d:/AssignmentFDE/infra/README.md). Updated [`README.md`](file:///d:/AssignmentFDE/README.md) with per-profile Local, Docker, and AWS deployment guides.
- **Completed Foundation Tasks:**
  - ✅ **Task 0:** [`00-base-layout-design-system.md`](file:///d:/AssignmentFDE/context/features/00-base-layout-design-system.md) (Atomic Design System, Pure Tailwind v4 `@theme`, English-First i18n, Paginated Table & AppShell)
  - ✅ **Task 1:** [`01-data-pack-and-ingestion.md`](file:///d:/AssignmentFDE/context/features/01-data-pack-and-ingestion.md) (Full-Stack Triple-Tab Ingestion Hub, Pre-flight CSV Check, Live X Lookup & 3-Tier Deduplication)
  - ✅ **Task 2:** [`02-database-and-state-machine.md`](file:///d:/AssignmentFDE/context/features/02-database-and-state-machine.md) (SQLite WAL Schema, 9-State Lifecycle Machine, Two-Tier Zero Double-Messaging Gate & Candidate Lifecycle API)
  - ✅ **Task 3:** [`03-auth-and-security.md`](file:///d:/AssignmentFDE/context/features/03-auth-and-security.md) (Next.js BFF HttpOnly Cookie Auth, 7-Day JWT, Pre-filled Partner Login, Protected FastAPI Middleware & Error Pages)
  - ✅ **Task 4:** [`04-dual-queue-and-ai-send-engine.md`](file:///d:/AssignmentFDE/context/features/04-dual-queue-and-ai-send-engine.md) (SQLite Dual Queue Worker, Tri-Guard AI Evaluator, Token Bucket Limiter & Dual-Mode Safe Send Dispatcher)
  - ✅ **Task 5:** [`05-hitl-review-and-composer-ui.md`](file:///d:/AssignmentFDE/context/features/05-hitl-review-and-composer-ui.md) (Table-First Review Workspace, Search/Filter Triage, Grounded Evidence Highlighting & Review/Composer Modal)
  - ✅ **Task 6:** [`06-outreach-ledger-and-dashboard.md`](file:///d:/AssignmentFDE/context/features/06-outreach-ledger-and-dashboard.md) (Immutable Outreach Ledger, Founder Reply Simulator/Tracker, Audit Trail Drawer & Partner Calibration Matrix)
  - ✅ **Task 8:** [`08-contract-and-playwright-e2e.md`](file:///d:/AssignmentFDE/context/features/08-contract-and-playwright-e2e.md) (Contract-Based Testing + Isolated Playwright E2E Quality Gate)
- **Current Status:** `FEATURE 07 CODE & IAC COMPLETE (RuntimeGateway + Sub-tasks 7.1–7.5 Implemented & Verified Offline/Static; Pending Live API Keys, Docker Desktop Daemon Runtime & AWS Terraform Apply)`

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
   - Auto-creates default Partner user (`partner@xscout.local`).
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
      - Implemented `ensure_default_partner_user` to guarantee the pre-filled Partner account (`partner@xscout.local` / `XScout2026!`) always exists in SQLite.
      - Built `get_current_user` FastAPI dependency supporting both `Authorization: Bearer <jwt>` header and `session_token` HttpOnly cookie, rejecting unauthenticated/expired requests with `401 Unauthorized`.
    - **FastAPI Auth Router (`backend/app/api/auth.py`):**
      - Implemented `POST /api/auth/login`, `POST /api/auth/demo-login`, `POST /api/auth/register`, `GET /api/auth/me`, and `POST /api/auth/logout`.
      - Protected `/api/candidates` router with `Depends(get_current_user)`.
    - **Next.js BFF Route Handlers, Private Route Middleware & Error Pages (`frontend/src/`):**
      - Built `POST /api/auth/login` and `POST /api/auth/logout` Next.js BFF route handlers managing the 7-day `HttpOnly` `session_token` cookie (`SameSite=Lax`).
      - Built [`frontend/src/middleware.ts`](file:///d:/AssignmentFDE/frontend/src/middleware.ts) enforcing private route protection on all workspace pages (`/`, `/ingestion`, `/workspace`, `/ledger`, `/calibration`), checking JWT expiration (`exp`), redirecting unauthenticated sessions to `/login?from=...`, and enforcing Partner role RBAC (`/403` for unauthorized roles).
      - Built `/login` page ([`login/page.tsx`](file:///d:/AssignmentFDE/frontend/src/app/login/page.tsx)) with pre-filled `partner@xscout.local` & `XScout2026!`, show/hide password toggle, language switcher (`EN`/`VI`), and 1-click sign-in.
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
15. ✅ **Full Implementation of Feature 08 ([`08-contract-and-playwright-e2e.md`](file:///d:/AssignmentFDE/context/features/08-contract-and-playwright-e2e.md)):**
    - **Contract Remediation & Selective `data-testid` Standard:** Fixed **BUG-01** (`StateMachineSummary` nested contract + fail-fast), **BUG-02** (`dispatch_mode` forwarding), **BUG-03** (`skip_ledger_collisions` & `queue_ai_enabled`), and the `rejectCandidate` flat `CandidateItem` response mismatch surfaced by `PW-03`; added selective `data-testid` attributes, `AI_FAILED` filter pill, isolated E2E env hooks, and i18n parity fixes.
    - **Tier 1 Contract-Based Testing ([`backend/tests/contracts/test_api_contracts.py`](file:///d:/AssignmentFDE/backend/tests/contracts/test_api_contracts.py)):** 6 contract & golden JSON diff checks against `backend/tests/contracts/expected/` (`state_summary_initial_seed.json`, `preflight_missing_bio.json`, `calibration_kpi.json`) -> **6/6 PASSED**.
    - **Tier 2 Isolated Playwright E2E Infrastructure (`frontend/e2e/` & `backend/tests/e2e_seed.py`):** Dedicated `localhost:3100` (`.next-e2e`) + `127.0.0.1:8001` (`outreach_e2e.db`, dev `outreach.db` untouched) with deterministic resets (`CLEAN_EMPTY`, `SEED_PACK_EVALUATED`) and Page Object Models (`LoginPage`, `IngestionPage`, `WorkspacePage`, `LedgerPage`).
    - **9 Risk-Ranked Playwright E2E Specs (`PW-01`..`PW-09`):** Covered auth/RBAC/Error500View, 5-state Happy Path + 409 double-send lock, Prompt Injection Shield + Reject, Closed DM Guard (`422 -> SEND_BLOCKED`), Sparse Profile Anti-Hallucination (`INSUFFICIENT_EVIDENCE`), `AI_FAILED` Fault Isolation & Retry, Cross-batch CSV Dedup/Pre-flight/Live Lookup, Ledger Audit Trail + Calibration Matrix (`100%`), and Bilingual EN/VI switching with zero console/page errors (**9/9 PASSED** twice consecutively).
    - **Quality Gate Runner (`tests/manual/`):** Created `config.sh`, `README.md`, `test-all.ps1`, `test-all.sh`, and configured `.gitignore` for generated results/traces/reports.
    - **Final Verification (after final code/test edit):**
      - `powershell -ExecutionPolicy Bypass -File tests/manual/test-all.ps1` -> **Tier 1 `6/6 PASSED` + Tier 2 `9/9 PASSED` (`exit code 0`)**.
      - `python -m pytest backend/tests/ -v` -> **35/35 PASSED in 5.68s**.
      - `cd frontend && npm.cmd run build` -> **15/15 static pages + Middleware (`32.3 kB`), 0 TypeScript/ESLint errors**.
16. ✅ **Feature 07 Progress – UI/Copy Polish + Sub-tasks 7.1, 7.2, 7.4 ([`07-verification-and-handover.md`](file:///d:/AssignmentFDE/context/features/07-verification-and-handover.md)):**
    - **UI/UX & Concise Product Copy Refinement:** Cleaned [`login/page.tsx`](file:///d:/AssignmentFDE/frontend/src/app/login/page.tsx) (removed prefilled badge pill & security note, button updated to `Sign In`/`Đăng nhập`), wrapped 4-card KPI block behind collapsible `[Show Metrics]`/`[Hide Metrics]` toggle in [`page.tsx`](file:///d:/AssignmentFDE/frontend/src/app/page.tsx), enforced single-line `whitespace-nowrap shrink-0` in [`ScorePill.tsx`](file:///d:/AssignmentFDE/frontend/src/components/atoms/ScorePill.tsx), shortened workspace/ingestion/ledger/calibration labels and column headers across [`en.json`](file:///d:/AssignmentFDE/frontend/src/locales/en.json) & [`vi.json`](file:///d:/AssignmentFDE/frontend/src/locales/vi.json), and updated [`pw-09-bilingual-i18n-console.spec.ts`](file:///d:/AssignmentFDE/frontend/e2e/specs/pw-09-bilingual-i18n-console.spec.ts).
    - **Sub-task 7.1 – Clean User-Only Reset ([`backend/reset_clean_users.py`](file:///d:/AssignmentFDE/backend/reset_clean_users.py)):** Deletes `job_queue`, `outreach_ledger`, `candidates` while keeping `users` (`partner@xscout.local`). Executed against `outreach.db` (`Users retained: 1`, `Candidates: 0`, `OutreachLedger: 0`, `JobQueue: 0`).
    - **Sub-task 7.2 – Live X OAuth 1.0a Client & Diagnostic Suite ([`x_client.py`](file:///d:/AssignmentFDE/backend/app/services/x_client.py), [`verify_live_keys.py`](file:///d:/AssignmentFDE/backend/scripts/verify_live_keys.py)):** Completed real X API v2 `POST /2/dm_conversations/with/{id}/messages` dispatch wiring in [`state_machine.py`](file:///d:/AssignmentFDE/backend/app/services/state_machine.py) + `LIVE_X_DRY_RUN` in [`config.py`](file:///d:/AssignmentFDE/backend/app/core/config.py) + HTTP `429`/`502` handling in [`candidates.py`](file:///d:/AssignmentFDE/backend/app/api/candidates.py), and 4 hermetic tests in [`test_verification_tools.py`](file:///d:/AssignmentFDE/backend/tests/test_verification_tools.py). Diagnostic probe confirms current `backend/.env` keys are unset (`SKIPPED_NO_KEY`).
    - **Sub-task 7.4 – Manual QA Checklist ([`tests/manual/MANUAL_QA_CHECKLIST.md`](file:///d:/AssignmentFDE/tests/manual/MANUAL_QA_CHECKLIST.md)):** Authored 18 checks across Groups A–F (`MQ-A1`..`MQ-F2`); checked off `MQ-A1` + full automated baseline.
17. ✅ **Centralized `RuntimeGateway` + Feature 07 Sub-tasks 7.3 & 7.5 (`OFFLINE_MOCK` / `HYBRID_AUTO` / `LIVE_PRODUCTION`):**
    - **`RuntimeGateway` Control ([`runtime_gateway.py`](file:///d:/AssignmentFDE/backend/app/core/runtime_gateway.py), `GET /api/system/runtime`):** Centralized AI, X Lookup, and DM Dispatch mode resolution across 3 `RUNTIME_PROFILE` values (`OFFLINE_MOCK`, `HYBRID_AUTO`, `LIVE_PRODUCTION`) with `execution_meta` provenance stamping and container DNS (`x-simulator` / `x_simulator`) support in `_is_localhost_url()` & [`x_client.py`](file:///d:/AssignmentFDE/backend/app/services/x_client.py); enabled SQLAlchemy `pool_pre_ping=True` in [`database.py`](file:///d:/AssignmentFDE/backend/app/core/database.py) + `psycopg[binary]>=3.2.0` in [`requirements.txt`](file:///d:/AssignmentFDE/backend/requirements.txt).
    - **Sub-task 7.3 – Docker Standalone Packaging & Compose ([`docker-compose.yml`](file:///d:/AssignmentFDE/docker-compose.yml), [`backend/Dockerfile`](file:///d:/AssignmentFDE/backend/Dockerfile), [`frontend/Dockerfile`](file:///d:/AssignmentFDE/frontend/Dockerfile)):** Configured Next.js `output: "standalone"`, added [`api-config.ts`](file:///d:/AssignmentFDE/frontend/src/lib/api-config.ts) (`NEXT_PUBLIC_API_BASE_URL=auto` for Zero-CORS multi-origin), [`healthz/route.ts`](file:///d:/AssignmentFDE/frontend/src/app/healthz/route.ts), HTTP-safe cookie deletion in [`logout/route.ts`](file:///d:/AssignmentFDE/frontend/src/app/api/auth/logout/route.ts), [`.env.docker.example`](file:///d:/AssignmentFDE/.env.docker.example), `.dockerignore`, Nginx [`infra/nginx/nginx.conf`](file:///d:/AssignmentFDE/infra/nginx/nginx.conf) (`--profile prod-sim`), and added `AUTO_SEED_LEDGER_BASELINE=False` (default in [`config.py`](file:///d:/AssignmentFDE/backend/app/core/config.py) & [`ledger_service.py`](file:///d:/AssignmentFDE/backend/app/services/ledger_service.py)) so fresh/reset builds stay strictly user-only (`1` user, `0` candidates, `0` ledger) until explicitly seeded.
    - **Sub-task 7.5 – AWS Terraform Multi-Env IaC & CI/CD ([`infra/terraform/`](file:///d:/AssignmentFDE/infra/terraform/), [`.github/workflows/ci-cd.yml`](file:///d:/AssignmentFDE/.github/workflows/ci-cd.yml), [`infra/README.md`](file:///d:/AssignmentFDE/infra/README.md), [`README.md`](file:///d:/AssignmentFDE/README.md)):** Built `versions.tf`, `backend.tf.example`, `main.tf`, `variables.tf`, `outputs.tf`, 4 modules (`network`, `alb`, `storage_secrets`, `ecs_cluster`), and 3 `.tfvars` environments mapped 1-1 with `RUNTIME_PROFILE` (`dev -> OFFLINE_MOCK` EFS+x-simulator; `staging -> HYBRID_AUTO` EFS+x-simulator; `prod -> LIVE_PRODUCTION` Multi-AZ RDS PostgreSQL 16 + AutoScaling); reorganized root [`README.md`](file:///d:/AssignmentFDE/README.md) with per-profile Local, Docker, and AWS deployment instructions.
    - **Verification (2026-11-14, after final edits):**
      - `cd frontend; npx.cmd tsc --noEmit` -> **0 TypeScript errors (exit code 0)**.
      - `cd frontend; npm.cmd run build` -> **16/16 routes (`output: "standalone"` + `/healthz`) + Middleware (`32.3 kB`), `server.js` generated (`True`), 0 errors**.
      - `python -m pytest backend\tests -v` -> **44 passed, 4 warnings in 9.47s** (including `test_clean_db_does_not_auto_seed_ledger_when_flag_disabled`).
      - `powershell -ExecutionPolicy Bypass -File tests/manual/test-all.ps1` -> **Tier 1 `6/6 PASSED` (3.74s) + Tier 2 Playwright E2E `9/9 PASSED` (3.8m) + Tier 3 E/R Result Contract `100% PASS`, exit code 0**.
      - `docker compose --env-file .env.docker --profile prod-sim down -v; docker compose --env-file .env.docker up --build -d` -> **all 3 containers (`genai-backend`, `genai-frontend`, `genai-x-simulator`) built and `healthy`**; verified `/api/auth/login` + `/api/candidates` + `/api/ledger` leaves `/app/data/outreach.db` clean (`users: 1, candidates: 0, outreach_ledger: 0, job_queue: 0`).
      - Static Terraform validator (`19 files, 4 modules, 3 environments`) -> **`TERRAFORM_STATIC_CHECK_OK` (exit code 0)**. *(`terraform` CLI not installed locally; native `terraform validate/plan` runs in GitHub Actions or CI host.)*
18. ✅ **Live X End-to-End Enhancements, SSR Runtime Injection, 5-Guard CSV Batch X Verification & Submission Deliverables (2026-11-15):**
    - **Live X DM Reply Sync (`POST /api/ledger/sync-replies`):**
      - Fixed OAuth 1.0a URL query parameter signing in `resolve_x_user_id()` (`?user.fields=id,username`) and implemented `fetch_x_dm_events(participant_id, max_results, timeout)` in `backend/app/services/x_client.py` calling `GET /2/dm_events` and `GET /2/dm_conversations/with/{participant_id}/dm_events` (`dm.read`).
      - Added `GET /2/dm_events` and `GET /2/dm_conversations/with/{participant_id}/dm_events` to `backend/scripts/x_simulator.py`.
      - Persisted `live_resp["participant_id"]` onto `candidate.x_user_id` upon live DM dispatch in `backend/app/services/state_machine.py`.
      - Added `sync_x_dm_replies(db)` (`backend/app/services/ledger_service.py`) and `POST /api/ledger/sync-replies` (`backend/app/api/ledger.py`) to detect inbound replies from target `x_user_id` and transition `SENT -> REPLIED` in both `OutreachLedger` and `Candidate`.
      - Wired `Sync X Replies` (`data-testid="btn-sync-x-replies"`) and `Live Auto-Sync (15s)` realtime polling toggle (`data-testid="btn-toggle-autosync-x"`) in `frontend/src/components/ledger/LedgerDashboardClient.tsx` and `frontend/src/lib/ledger-api.ts`.
      - Added unit test `test_sync_x_dm_replies_transitions_sent_to_replied` in `backend/tests/test_ledger_and_calibration.py`.
    - **SSR Runtime Injection (`RuntimeProvider`) & UI Refinements:**
      - Created `frontend/src/context/runtime.tsx` (`RuntimeProvider`, `useRuntime()`) and updated `frontend/src/components/providers/AppProviders.tsx` and `frontend/src/app/layout.tsx` (`export const dynamic = "force-dynamic"`) to inject `RUNTIME_PROFILE` and `DISPATCH_MODE` directly from the Next.js Server Component (`process.env` with SSR fallback to `${BACKEND_INTERNAL_URL}/health`) with zero client-side loading flicker.
      - Injected `RUNTIME_PROFILE` and `DISPATCH_MODE` into the `frontend` service in `docker-compose.yml` and `infra/terraform/modules/ecs_cluster/main.tf`.
      - Updated `frontend/src/app/ingestion/page.tsx` to hide the `Starter Pack` (`seed`) tab and default `activeTab` to `"live"` synchronously when `runtimeProfile === "LIVE_PRODUCTION"`.
      - Updated `frontend/src/app/page.tsx` (`/workspace`) and `frontend/src/components/organisms/ReviewComposerModal.tsx` to default `dispatchMode` to `"LIVE_X"` when `runtimeProfile === "LIVE_PRODUCTION"`.
      - Refined active sidebar menu item styling in `frontend/src/components/organisms/AppSidebar.tsx` to a soft light-active theme (`bg-primary/10 text-primary font-semibold border border-primary/15`, icon `text-primary`, badge `bg-primary/15 text-primary`).
    - **5-Guard Live X API CSV Batch Verification & Enrichment (`verify_with_x_api`):**
      - Added `verify_with_x_api: bool = False` to `CsvPreflightRequest` and `CsvIngestRequest` in `backend/app/schemas/candidate.py` (preserving 100% compatibility with Golden Contract `CT-02` when `False`).
      - Updated `preflight_csv_check` and `parse_csv_content` in `backend/app/services/ingestion.py` so that when `verify_with_x_api=True`, only the `handle` column is required and batch size is guarded at `MAX_CSV_X_VERIFY_BATCH = 25` rows per upload.
      - Implemented `_batch_fetch_x_profiles_and_tweets(handles)` in `backend/app/services/ingestion.py` and integrated it into `ingest_candidate_batch` **after** 3-tier deduplication (in-batch dedup, existing DB `Candidate` dedup, and `OutreachLedger` `SENT`/`REPLIED` suppression), executing 1 batch user lookup (`GET /2/users/by?usernames=h1,h2,...`) + bounded-concurrency timeline lookups (`GET /2/users/{uid}/tweets?max_results=5` via `ThreadPoolExecutor(max_workers=3)`), overwriting stale/missing CSV fields (`name`, `bio`, `followers`, `recent_tweets`, `x_user_id`, `raw_profile_json`) with live X data and skipping `404` non-existent handles (`SKIPPED_X_NOT_FOUND`).
      - Added `GET /2/users/by` batch lookup endpoint to `backend/scripts/x_simulator.py`.
      - Wired `verifyWithX` checkbox (`data-testid="csv-verify-x-checkbox"`) in `frontend/src/components/ingestion/CsvUploadTab.tsx` and `frontend/src/lib/ingestion-api.ts` (defaulting to `true` in `LIVE_PRODUCTION` and `false` otherwise, re-triggering preflight on toggle).
      - Added handle-only CSV `verify_with_x_api=True` API test in `backend/tests/test_ingestion.py`.
    - **Environment-Aware CSV Templates & Live X Lookup Hygiene:**
      - Updated `getCsvTemplateForRuntime` (`frontend/src/lib/ingestion-api.ts`), `CsvUploadTab.tsx`, and `GET /api/ingestion/template` (`backend/app/api/ingestion.py`) so `OFFLINE_MOCK`/`HYBRID_AUTO` download the populated simulator sample (`xscout_sample_candidates_mock.csv`), whereas `LIVE_PRODUCTION` downloads a clean **header-only blank template** (`xscout_live_x_template.csv` -> `handle,segment` with `verifyWithX`, or full manual headers if unchecked) accompanied by a clear bilingual policy note banner (`live-csv-policy-note`) to avoid synthetic handles or unwanted X API credit spend.
      - Updated `CsvUploadTab.tsx` column status badges to distinguish required `handle` vs `Synced via X API` optional columns when `verifyWithX=true`, and updated `LiveXLookupTab.tsx` to start blank and hide synthetic `QUICK_HANDLES` (`@minh_quant`, `@arjun_infer`, `@linhtran_robo`) in `LIVE_PRODUCTION`.
      - Upgraded Live X Pre-flight Data Preview (`backend/app/services/ingestion.py`, `backend/app/schemas/candidate.py`, `CsvUploadTab.tsx`): strips UTF-8 BOM & blank separator rows, performs `$0` local DB/Ledger dedup inspection on file upload, validates X handle syntax (`is_valid_x_username`: `[A-Za-z0-9_]{1,15}`, filtering invalid handles like `T.Yamazaki` as `SKIPPED_INVALID_X_HANDLE` so one bad handle never triggers X API `400 Invalid Request` for the whole batch), shows tailored Live X columns (`Handle`, `Target Segment`, `Live X Profile`, `Dedup Guard`, `Validation`), adds optional 1-call `fetch_x_preview=true` (`GET /2/users/by`) preview button (`csv-preview-x-btn`), hides broken empty preview table on 0-row CSVs in favor of localized guidance while keeping empty-batch protection (`valid=False`), and adds an inline `"Paste X handles / CSV"` editor (`csv-paste-toggle`).
      - Added unit assertions for `/api/ingestion/template` and `fetch_x_preview` across `OFFLINE_MOCK` and `LIVE_PRODUCTION` in `backend/tests/test_ingestion.py`.
    - **Submission Deliverables & Native Terraform Verification:**
      - Created 1-page architecture and trade-offs write-up in `ARCHITECTURE_AND_WRITEUP.md` and 3–5 minute bilingual demo script in `DEMO_VIDEO_SCRIPT.md`.
      - Installed native HashiCorp Terraform `v1.17.1` (`windows_amd64`) and verified `terraform init -backend=false`, `terraform validate`, and `terraform fmt -check -recursive` across `infra/terraform`.
19. ✅ **Dedicated DM Draft Regeneration (`POST /api/candidates/{id}/regenerate-dm`) & Partner Fit Score Override (`POST /api/candidates/{id}/override-fit`) (2026-11-15):**
    - **DM Draft Regeneration Isolation:**
      - Fixed a bug in `ReviewComposerModal` -> `candidates-api.ts` where clicking **"Regenerate with AI"** inside **Personalized DM Composer** called `POST /api/queue/evaluate/{id}`, which re-ran full AI evaluation, mutated **AI Fit Assessment (Why They Fit)** (`fit_reason` / `fit_score`), left stale `edited_dm` shadowing `draft_dm`, or produced identical/empty copy.
      - Added [`regenerate_candidate_dm_draft`](file:///d:/AssignmentFDE/backend/app/services/ai_evaluator.py) + [`regenerate_candidate_dm_by_id`](file:///d:/AssignmentFDE/backend/app/services/queue_worker.py) + `POST /api/candidates/{candidate_id}/regenerate-dm` ([`candidates.py`](file:///d:/AssignmentFDE/backend/app/api/candidates.py)) to generate ONLY a fresh `draft_dm` variation (Gemini/OpenAI `temperature=0.7` in `LIVE_PRODUCTION`, distinct multi-variant grounded composer in `OFFLINE_MOCK`, Layer 1/3 injection & sparse guards returning HTTP `422`, terminal `SENT`/`REPLIED` protection returning HTTP `409`), clear `edited_dm`, and leave `fit_score`, `fit_reason`, and `is_match` untouched.
      - Updated [`candidates-api.ts`](file:///d:/AssignmentFDE/frontend/src/lib/candidates-api.ts), [`page.tsx`](file:///d:/AssignmentFDE/frontend/src/app/page.tsx), and [`ReviewComposerModal.tsx`](file:///d:/AssignmentFDE/frontend/src/components/organisms/ReviewComposerModal.tsx) to call `/regenerate-dm` with `current_dm` and immediately sync `<Textarea data-testid="dm-composer-textarea">`.
    - **Partner Fit Score Override with Rationale (`requirement.md` line 65):**
      - Implemented [`override_candidate_fit_score`](file:///d:/AssignmentFDE/backend/app/services/state_machine.py) and `POST /api/candidates/{candidate_id}/override-fit` ([`candidates.py`](file:///d:/AssignmentFDE/backend/app/api/candidates.py)) allowing a Partner to override `fit_score` (`1..4`) with a mandatory rationale (`reason >= 3` chars), tagging `fit_reason` with `[Partner Override (X/4)] ...`, updating `is_match` (`>=3`), moving `QUEUED_FOR_AI`/`AI_FAILED`/`INSUFFICIENT_EVIDENCE` into `PENDING_REVIEW`, auto-populating an initial grounded `draft_dm` when upgrading a low-scored candidate to `>=3`, and protecting terminal `SENT`/`REPLIED` states (`409 Conflict`).
      - Added inline **Override Score / Ghi đè điểm** panel (`data-testid="toggle-override-fit-btn"`, `override-fit-panel`, `override-score-btn-1..4`, `override-reason-input`, `save-override-fit-btn`) inside the **AI Fit Assessment (Why They Fit)** section of [`ReviewComposerModal.tsx`](file:///d:/AssignmentFDE/frontend/src/components/organisms/ReviewComposerModal.tsx), wired `overrideCandidateFitScore` in [`candidates-api.ts`](file:///d:/AssignmentFDE/frontend/src/lib/candidates-api.ts) & [`page.tsx`](file:///d:/AssignmentFDE/frontend/src/app/page.tsx), added symmetrical EN/VI translations in [`en.json`](file:///d:/AssignmentFDE/frontend/src/locales/en.json) & [`vi.json`](file:///d:/AssignmentFDE/frontend/src/locales/vi.json), and added unit tests `test_regenerate_dm_preserves_fit_assessment_and_updates_draft` and `test_partner_override_fit_score_with_reason` in [`test_dual_queue_and_ai.py`](file:///d:/AssignmentFDE/backend/tests/test_dual_queue_and_ai.py) (`47/47` backend tests passing).

---

## 3. Next Immediate Steps (Feature 07 Remaining Manual/Ops Sign-Off)
1. **Run Live Key Smoke & Benchmark (when real API keys are populated in `backend/.env`):**
   - `python -m backend.scripts.verify_live_keys --mode all --full-benchmark --json-out tests/manual/results/live-verify-report.json`
2. **Docker Compose Runtime Verification (when Docker Desktop daemon is running):**
   - `docker compose --env-file .env.docker up --build -d` (preserving `genai_sqlite_data` volume across restarts).
3. **AWS Provisioning (when ready to deploy to AWS account):**
   - `cd infra/terraform && terraform init && terraform plan -var-file="environments/dev.tfvars"`, populate `<env>/genai-fde/app-secrets` in Secrets Manager, and verify `GET /api/system/runtime` (`live_production_readiness.ready == true`) on `staging` before `prod` cutover.
