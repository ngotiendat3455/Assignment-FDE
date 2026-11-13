# Manual QA & Pre-Release Verification Checklist (Sub-task 7.4)

> **Purpose:** Human exploratory & visual verification complementing automated Tier 1 Contract Tests (`6/6`) and Tier 2 Playwright E2E (`9/9`).  
> **Reference Spec:** [`context/features/07-verification-and-handover.md`](file:///d:/AssignmentFDE/context/features/07-verification-and-handover.md#L120-L176)

---

## Run Header (Fill per Verification Cycle)

- **Tester / Reviewer:** `____________________`
- **Date / Commit:** `2026-11-13` (Feature 07 Sub-tasks 7.1 / 7.2 / 7.4 Setup)
- **Target URL:** Local (`http://localhost:3000` / `http://127.0.0.1:8000`) | Docker | Staging
- **Live Key Status (`backend/.env`):**
  - `GEMINI_API_KEY` / `OPENAI_API_KEY`: ☑ Configured & Live Smoke Passed (`gemini-3.5-flash`, `L1_LIVE_LLM` 3/3 PASSED, `0` guard failures)
  - `X_BEARER_TOKEN` (Live Lookup): ☐ Configured & Tested | ☑ Currently Unset (`SKIPPED_NO_KEY`)
  - `X_ACCESS_TOKEN*` (Live DM `LIVE_X`): ☐ Configured & Tested | ☑ Currently Unset (`SKIPPED_NO_KEY`)

---

## Automated Pre-Requisites (Must Pass Before Manual Sign-off)

| Check | Command | Status | Notes |
| :--- | :--- | :--- | :--- |
| Clean Reset CLI Test + Live Client Unit Tests | `python -m pytest backend/tests/ -v` | Passed (`39 passed in 8.81s`) | Isolated offline via `backend/tests/conftest.py` |
| Frontend Build & Lint | `cd frontend && npm.cmd run build` | Passed (`0 errors`) | 15/15 static routes + Edge Middleware |
| Quality Gate (Contracts + Playwright E2E) | `powershell -ExecutionPolicy Bypass -File tests/manual/test-all.ps1` | Passed (`6/6` Tier 1 + `9/9` Tier 2 in `2.7m`) | Verified full E2E including updated UI/copy polish |

---

## Group A: Clean User-Only Reset, Auth & UI Polish

- [x] **MQ-A1 — Clean User-Only Reset (`backend/reset_clean_users.py`):**
  - **Command:** `python -m backend.reset_clean_users --yes` (add `--with-analyst` to include RBAC analyst user).
  - **Expected:** Prints `Users retained: 1 (partner@genaifund.ai [role=partner])`, `Candidates: 0`, `OutreachLedger: 0`, `JobQueue: 0`.
  - **Observed (2026-11-13):** Executed cleanly on `sqlite:///./outreach.db` — verified `Users retained: 1`, `Candidates: 0`, `OutreachLedger: 0`, `JobQueue: 0`.
- [ ] **MQ-A2 — Login Page UI Polish (`/login`):**
  - **Steps:** Open `http://localhost:3000/login`.
  - **Expected:**
    - Pill `"Reviewer Ready • Pre-filled Partner Account"` is **removed**.
    - Security note footer (`Zero XSS exposure`) is **removed**.
    - Heading & Submit CTA display cleanly as `"Sign In"` (EN) / `"Đăng nhập"` (VI).
- [ ] **MQ-A3 — Clean Empty Workspace & Collapsible KPIs (`/`):**
  - **Steps:** Sign in as `partner@genaifund.ai` -> land on `/` (`Candidate Review`).
  - **Expected:**
    - 4 KPI cards (`DM DISPATCHED`, `REPLIES RECEIVED`, `NEEDS ATTENTION`, `SAFETY BLOCKED`) are **collapsed by default**.
    - Clicking `[Show Metrics]` expands all 4 cards cleanly; clicking `[Hide Metrics]` collapses them again.
    - Candidate table shows empty state (`0` candidates) with no errors.
- [ ] **MQ-A4 — RBAC `/403` & Session `/401`:**
  - **Steps:** Run reset with `--with-analyst`, log in as `analyst@genaifund.ai` (`Analyst2026!`), visit `/calibration` -> redirects to `/403`. Clear `session_token` cookie -> redirects to `/login`.

---

## Group B: Ingestion 3 Journeys & Live X Lookup

- [ ] **MQ-B1 — Starter Pack Ingestion (`/ingestion` -> Tab 1 `Starter Pack`):**
  - **Steps:** Click `"Load Starter Pack"` (`Nạp gói mẫu`).
  - **Expected:** Audit Card shows 20 rows parsed, `P002`/`P020` in-batch duplicate merged (`1`), newly queued profiles (`19` on user-only DB; or `16` + `3` collisions if seed history exists).
- [ ] **MQ-B2 — CSV Pre-flight & Batch Import (Tab 2 `CSV Import`):**
  - **Steps:** Upload malformed CSV missing `bio` column -> Pre-flight marks `Missing Column` and disables `"Import CSV"`. Upload valid CSV -> imports cleanly.
- [ ] **MQ-B3 — Live X Handle Lookup (Tab 3 `X Lookup` — Requires `X_BEARER_TOKEN`):**
  - **Pre-req:** `python -m backend.scripts.verify_live_keys --mode x --handle OpenAI` returns `PASSED`.
  - **Steps:** Enter `@OpenAI` (or a public SEA founder handle) in UI lookup input -> Click `"Lookup on X"`.
  - **Expected:** Top banner shows `"X API v2 Connected (Live Mode)"`, profile bio & recent tweets match live X profile.

---

## Group C: Live AI Scoring & Tri-Guard Inspection (Requires `GEMINI_API_KEY` or `OPENAI_API_KEY`)

- [ ] **MQ-C1 — Real LLM Diagnostic & Calibration Benchmark (CLI):**
  - **Command:** `python -m backend.scripts.verify_live_keys --mode llm --full-benchmark --json-out tests/manual/results/live-verify-report.json`
  - **Expected:** `status == "PASSED"`, `guard_failures == []`, acceptable latency & cost printed.
- [ ] **MQ-C2 — Live Queue Scoring & `ScorePill` Single-Line Rendering (`/`):**
  - **Steps:** Click `"Process Queue"` on Candidate Review table after ingesting profiles.
  - **Expected:**
    - `ScorePill` (`4 / 4`, `3 / 4`, `1 / 4`) renders on **exactly 1 horizontal line** (never wraps `"4 /"` and `"4"` onto 2 lines).
    - Open `"Review"` modal on a `4 / 4` candidate -> Amber `<EvidenceMark>` highlight quotes verbatim text from bio/tweets; Draft DM is 250–600 chars, grounded & peer-to-peer.
- [ ] **MQ-C3 — Tri-Guard Live Resilience (`P017` Prompt Injection & `P018` Sparse):**
  - **Steps:** Filter/search `ignore_rules_ai` (or `override_bot99`) -> Score is `1 / 4`, DM empty (`REJECTED`/blocked). Search `mystic_coder99` -> `INSUFFICIENT_EVIDENCE` (`0 / 4`), DM empty.
- [ ] **MQ-C4 — Live DM Regenerate & Edit:**
  - **Steps:** Open `"Review"` modal, click `"Regenerate with AI"` -> New grounded draft returns cleanly without timeout; edit message and verify live char counter updates.

---

## Group D: Safety Guards (`SANDBOX` vs `LIVE_X`) & Idempotency

- [ ] **MQ-D1 — Closed DM Protection (`P019` `@arjun_infer`):**
  - **Expected:** `"Approve & Send"` button disabled in modal; red closed-DM alert displayed.
- [ ] **MQ-D2 — Happy Path Send + 409 Double-Send Lock:**
  - **Steps:** Open fit candidate (`@minh_quant`), send in `SANDBOX` mode -> transitions to `SENT`. Re-open `@minh_quant` -> `"Zero Double-Messaging Guard"` banner locks repeat sending.
- [ ] **MQ-D3 — `LIVE_X` Whitelist Safety & Controlled Real Send (Requires OAuth 4 keys):**
  - **Steps:** Set `DISPATCH_MODE=LIVE_X` and `ALLOWED_TEST_HANDLES=<your_own_test_handle>`. Verify non-whitelisted handle returns `422` (`SEND_BLOCKED`), while whitelisted handle returns `200` with real `dm_event_id` (or dry-run check via `verify_live_keys --mode dispatch`).

---

## Group E: Outreach Log, Calibration & Bilingual Product Copy

- [ ] **MQ-E1 — Outreach Log Single-Word Headers (`/ledger`):**
  - **Expected:** Table columns display `ID`, `Candidate`, `Message`, `Channel`, `Reply`, `Actions` (`Mã`, `Ứng viên`, `Tin nhắn`, `Kênh`, `Phản hồi`, `Thao tác`); action button displays `"Log Reply"` (`"Ghi phản hồi"`).
- [ ] **MQ-E2 — Founder Reply & Audit Trail Drawer:**
  - **Steps:** Click `"Log Reply"` -> submit sample reply -> `NEEDS ATTENTION` / `URGENT` badge appears -> Open Audit Trail -> Click `"Mark Handled"` -> resolves flag.
- [ ] **MQ-E3 — Calibration Matrix (`/calibration`):**
  - **Expected:** Table columns display `Profile`, `Segment`, `AI Score`, `Ref Score`, `Alignment`, `Notes` (`Hồ sơ`, `Nhóm`, `Điểm AI`, `Điểm chuẩn`, `Khớp chuẩn`, `Ghi chú`); verify accuracy readout.
- [ ] **MQ-E4 — EN ↔ VI Switch Across All Routes:**
  - **Steps:** Switch language on user menu between `EN` and `VI` on `/`, `/ingestion`, `/ledger`, `/calibration` -> Zero raw keys (`workspace.*`, `ledger.*`), concise product copy throughout.

---

## Group F: Docker Compose & AWS Deployment Smoke *(Executed in Sub-tasks 7.3 & 7.5)*

- [ ] **MQ-F1 — Docker Compose Health:** `docker compose up --build -d` -> `frontend` and `backend` both healthy, `/api/health` returns `200`.
- [ ] **MQ-F2 — Volume Persistence Across Restart:** Ingest & send 1 DM via Docker UI -> `docker compose restart backend` -> reload page -> records still present.

---

## Sign-off

- **Passed:** `___ / 18` checks
- **Blocked / Deferred (Reason):** `Live X/AI key checks (MQ-B3, MQ-C1..C4, MQ-D3) require real API keys in backend/.env; Docker checks (MQ-F1..F2) deferred to Sub-task 7.3.`

