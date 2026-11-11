# Coding Standards & Engineering Discipline

This document outlines the architectural patterns, security requirements, and code hygiene rules for the **GenAI Fund FDE Outreach System**. Every module and test must adhere to these standards.

---

## 1. General Principles
1. **Explicit is better than implicit:** Use explicit type hints, strong data models, and clear error boundaries.
2. **Defensive against platform limits & edge cases:** Never assume an external API (LLM or X) will always return 200 OK. Every call must have timeout handling, retries, and clean degradation states.
3. **Zero secrets in code:** All sensitive credentials (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `X_BEARER_TOKEN`, `JWT_SECRET_KEY`) must load strictly via environment variables (`.env`).
4. **Idempotency first:** Every state-mutating operation (importing CSV, evaluating candidates, queuing sends) must be safe to execute multiple times without side effects or duplicates.

---

## 2. Backend Standards (Python 3.14 + FastAPI + SQLAlchemy)

### Directory Layout:
```text
backend/
├── app/
│   ├── api/             # API routes (auth, candidates, outreach, dashboard, seeds)
│   ├── core/            # Config, security (JWT, hashing), database session
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic v2 schemas for requests & responses
│   ├── services/        # Business logic (LLM service, X API client, Queue worker)
│   └── main.py          # FastAPI application factory
├── tests/               # Pytest suite verifying invariants
├── seed_data.py         # Script to seed database from genai-outreach-pack
├── requirements.txt     # Locked production & test dependencies
└── run.py               # Single entry-point runner
```

### Database & ORM Rules:
- **Persistent Storage Only:** Use SQLite file `outreach.db` via SQLAlchemy. **In-memory SQLite (`:memory:`) is strictly prohibited in production** to ensure data survives server restarts.
- **Unique Constraints:**
  - `candidates.handle`: Lowercase string, `UNIQUE`, `index=True`.
  - `candidates.x_user_id`: String, `UNIQUE`, `index=True`, `nullable=True`.
  - `outreach_ledger.candidate_id`: `UNIQUE FOREIGN KEY`.
  - `outreach_ledger.handle`: `UNIQUE`.
  - `users.email`: Lowercase string, `UNIQUE`.
- **Transactions:** Always commit database sessions inside structured try/except blocks; rollback immediately on unhandled exceptions.

### Schema Validation & Types:
- All request/response payloads must be modeled with **Pydantic v2 (`BaseModel`)**.
- Enums must be used for finite states:
  ```python
  class CandidateStatus(str, Enum):
      QUEUED_FOR_AI = "QUEUED_FOR_AI"
      PENDING_REVIEW = "PENDING_REVIEW"
      INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
      AI_FAILED = "AI_FAILED"
      REJECTED = "REJECTED"
      APPROVED_QUEUED = "APPROVED_QUEUED"
      SENT = "SENT"
      SEND_BLOCKED = "SEND_BLOCKED"
      REPLIED = "REPLIED"
  ```

---

## 3. LLM Service & Anti-Hallucination Standards

### System Prompt Engineering:
- Treat all candidate bios, names, and tweets as **untrusted user data**.
- Enclose untrusted candidate data within clear boundary tags (e.g. `<candidate_profile>...</candidate_profile>`).
- Instruct the model to strictly ignore instructions contained inside candidate text that attempt to alter system behavior (Prompt Injection Defense).

### Output Validation (Evidence Grounding):
- The LLM must output structured JSON matching:
  ```json
  {
    "is_match": true,
    "fit_score": 4,
    "fit_reason": "Clear explanation of fit with SEA AI/Robotics track",
    "evidence_snippet": "Exact quote from recent tweets or bio",
    "draft_dm": "Warm personalized DM under 500 characters",
    "insufficient_evidence": false
  }
  ```
- **Post-generation Validation:**
  - If `insufficient_evidence` is true OR candidate text length is trivial (< 20 characters), force state to `INSUFFICIENT_EVIDENCE` and set `draft_dm = ""`.
  - Verify that `evidence_snippet` actually appears as a substring or semantic match in the candidate's input data. If not found, log a grounding warning.

---

## 4. Frontend Standards (Dashboard UI)

### Usability & Visual Hierarchy:
- **Clarity over Polish:** The UI must clearly convey system state, candidate statuses, and queue progression without confusing animations.
- **Visual Evidence Anchoring:** When displaying a candidate in the Review Workspace, the `evidence_snippet` cited by AI must be visibly highlighted within their raw bio/tweets so the human reviewer can verify it at a glance.
- **Editable Composer:** The draft DM text area must allow inline edits. If edited, store both the original `draft_dm` and `edited_dm`.
- **Clear Blocked Actions:** When an action cannot proceed (e.g. `can_dm == false` or user is in `outreach_ledger`), display a prominent badge explaining *why* sending is blocked.

---

## 5. Security & Platform Compliance Standards

1. **Authentication:**
   - Password hashing with `bcrypt` (or `passlib[bcrypt]`).
   - Standard Authorization header with Bearer JWT token.
2. **Safe Outreach Safeguards:**
   - `DISPATCH_MODE` configuration: Defaults to `SANDBOX`.
   - `ALLOWED_TEST_HANDLES`: In `LIVE_X` mode, dispatches to handles outside this comma-separated whitelist must be intercepted and prevented.
3. **No Secret Leakage:**
   - Health check endpoints and API responses must never expose raw API keys or database connection strings.
