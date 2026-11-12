# Current Active Feature: Feature 03 – Authentication, Security Hygiene & Demo Login
*(Sprint Status & Active Tracking)*

---

## 1. Active Feature Info
- **Active Task:** WBS Task 3 (BFF Auth, 7-Day HttpOnly Session, Pre-filled Login & API Guards): [`03-auth-and-security.md`](file:///d:/AssignmentFDE/context/features/03-auth-and-security.md)
  - ✅ **Sub-task 3.1 (Backend Security Core & `get_current_user` Guard):** Upgraded [`backend/app/core/config.py`](file:///d:/AssignmentFDE/backend/app/core/config.py) (7-day token = `10080` mins) and [`backend/app/core/security.py`](file:///d:/AssignmentFDE/backend/app/core/security.py) with salted password hashing, JWT creation/verification, `ensure_default_partner_user`, and `get_current_user` FastAPI dependency (supporting both `Authorization: Bearer` header and `session_token` HttpOnly cookie).
  - ✅ **Sub-task 3.2 (Backend FastAPI Auth Router & Route Protection):** Created [`backend/app/api/auth.py`](file:///d:/AssignmentFDE/backend/app/api/auth.py) (`POST /api/auth/login`, `POST /api/auth/demo-login`, `POST /api/auth/register`, `GET /api/auth/me`, `POST /api/auth/logout`), protected `/api/candidates` with `Depends(get_current_user)`, and wired into [`backend/app/main.py`](file:///d:/AssignmentFDE/backend/app/main.py).
  - ✅ **Sub-task 3.3 (Automated Pytest Suite for Auth & Security):** Created [`backend/tests/test_auth.py`](file:///d:/AssignmentFDE/backend/tests/test_auth.py) verifying all Acceptance Criteria in `03-auth-and-security.md` (`401 Unauthorized` on unauthenticated `/api/candidates`, 1-click pre-filled login with `partner@genaifund.ai`, `401` on wrong password, expired/tampered JWT rejection, logout cookie clearing, and zero secret key leakage) -> **5/5 PASSED** (`19/19` total backend tests).
  - ✅ **Sub-task 3.4 (Frontend Next.js BFF Auth Routes, Pre-filled `/login` Page & Header Session Controls):** Created [`frontend/src/app/api/auth/login/route.ts`](file:///d:/AssignmentFDE/frontend/src/app/api/auth/login/route.ts), [`frontend/src/app/api/auth/logout/route.ts`](file:///d:/AssignmentFDE/frontend/src/app/api/auth/logout/route.ts), [`frontend/src/app/login/page.tsx`](file:///d:/AssignmentFDE/frontend/src/app/login/page.tsx) (Wireframe 1 with pre-filled `partner@genaifund.ai` / `GenAIFund2026!`), updated [`TopHeader.tsx`](file:///d:/AssignmentFDE/frontend/src/components/organisms/TopHeader.tsx) (Wireframe 2), and added symmetrical i18n keys (`en.json` & `vi.json`).
  - ✅ **Sub-task 3.5 (End-to-End Verification & Sprint Log Update):** Verified `python -m pytest backend/tests/ -v` (`19 passed`) and `npm run build` in `frontend/` (`9/9 routes generated, 0 errors`).
- **Completed Foundation Tasks:**
  - ✅ **Task 0:** [`00-base-layout-design-system.md`](file:///d:/AssignmentFDE/context/features/00-base-layout-design-system.md) (Atomic Design System, Pure Tailwind v4 `@theme`, English-First i18n, Paginated Table & AppShell)
  - ✅ **Task 1:** [`01-data-pack-and-ingestion.md`](file:///d:/AssignmentFDE/context/features/01-data-pack-and-ingestion.md) (Full-Stack Triple-Tab Ingestion Hub, Pre-flight CSV Check, Live X Lookup & 3-Tier Deduplication)
  - ✅ **Task 2:** [`02-database-and-state-machine.md`](file:///d:/AssignmentFDE/context/features/02-database-and-state-machine.md) (SQLite WAL Schema, 9-State Lifecycle Machine, Two-Tier Zero Double-Messaging Gate & Candidate Lifecycle API)
  - ✅ **Task 3:** [`03-auth-and-security.md`](file:///d:/AssignmentFDE/context/features/03-auth-and-security.md) (Next.js BFF HttpOnly Cookie Auth, 7-Day JWT, Pre-filled Partner Login & Protected FastAPI Routes)
- **Next Spec Reference:** [`04-dual-queue-and-ai-send-engine.md`](file:///d:/AssignmentFDE/context/features/04-dual-queue-and-ai-send-engine.md)
- **Current Status:** `COMPLETED (Feature 03)`

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

---

## 3. Next Immediate Steps (Task 4 & Task 3 Backend Execution)
1. **Implement AI Fit Scorer & Grounded DM Service (`backend/app/services/ai_scorer.py`):**
   - Google Gemini Flash / OpenAI client integration with structured Pydantic schema output.
   - Prompt Injection Defense (Fortified Delimiters `<untrusted_candidate_data>` against `P017`).
   - Sparse profile detection (`insufficient_evidence = true` for `P018`).
   - Evidence Grounding Guard (assert `evidence_snippet` is a valid substring of raw bio/tweets).
2. **Implement Safe Send Dispatcher Service (`backend/app/services/dispatcher.py`):**
   - Dual-Mode dispatch: Sandbox Simulator vs. Live X API.
   - Rate limiting via Token Bucket.
   - Closed DM protection (`can_dm = false` -> `SEND_BLOCKED`).
   - Safety whitelist enforcement (`ALLOWED_TEST_HANDLES`).
3. **Build FastAPI REST API Endpoints:**
   - `/api/auth` (Register, Login, Me, 1-Click Demo Login)
   - `/api/candidates` (List with filters, Ingest Seed, Ingest CSV, Ingest Single Handle)
   - `/api/outreach` (Approve & Send, Reject, Record Reply)
   - `/api/dashboard` (KPIs, Ledger list, Calibration benchmark)
