# AI Agent Interaction Guidelines & Operating Protocol

This document governs how the AI Assistant and developer collaborate on this codebase. It ensures context continuity, prevents hallucinations, and enforces verification before marking tasks complete.

---

## 1. Context Navigation Protocol
Before writing any code or modifying existing modules, the AI Agent must:
1. **Check Current State:** Read `context/current-feature.md` to identify the active task, goals, and open checklists.
2. **Review Feature Spec:** Read the corresponding spec in `context/features/<feature-id>.md`.
3. **Respect Invariants:** Adhere strictly to the 7 core invariants in `context/project-overview.md` and standards in `context/coding-standards.md`.

---

## 2. Working Methodology: Small, Verified Steps
- **No Grand Sweeping Changes:** Build incrementally. Implement models first, then services, then API routes, then UI components.
- **Test-Driven Verification:** Every critical component (deduplication, prompt injection, evidence grounding, auth permissions) must have automated tests in `backend/tests/`.
- **Never Fake Working State:** Never declare a feature "done" if it hasn't been executed and verified in the environment.

---

## 3. Maintenance of `current-feature.md`
The file `context/current-feature.md` is the live dashboard of ongoing work.
- When beginning a subtask: Mark status as `IN_PROGRESS`.
- When encountering an obstacle or making a design trade-off: Log it under `### Blockers & Trade-offs`.
- When completing a subtask: Check off the item `[x]` and update `### Next Immediate Steps`.
- When a full feature is finished: Transition `current-feature.md` to point to the next feature spec.

---

## 4. Prompt Engineering & Defense Protocol
When generating or modifying LLM prompts inside the codebase:
- Always separate system instructions from candidate input data.
- Never concatenate untrusted strings into system prompts without delimiter tags.
- Always enforce JSON structured outputs using Pydantic schemas or explicit response format schemas.
- Ensure automated tests run against adversarial samples (`P017.json` / prompt injection) to confirm robustness.

---

## 5. Clean Machine Handover Checklist
Before finalizing work for user submission:
1. Ensure the backend can initialize its database and seed data with a single command.
2. Verify that `.env.example` lists every configuration variable with a sensible default or dummy placeholder.
3. Test that no proprietary API keys, personal secrets, or live user tokens are hardcoded.
4. Verify that running tests passes with zero failures.
