# X-Scout AI – Outreach & Evaluation Data Pack (`genai-outreach-pack`)

**All data in this folder is synthetic.** Every X profile, handle, user ID, post, and outreach log entry was crafted specifically for evaluating and testing the X-Scout AI FDE Outreach Prototype. None of it describes a real person or triggers unsolicited real-world messaging.

This data pack represents an export from X-Scout AI's Southeast Asia (SEA) AI & Robotics scouting workflow as of **10 November 2026**.

## Purpose of This Data Pack

While your prototype must support **live X API connections** (for fetching real profiles and sending real DMs to controlled test accounts), X API rate limits and tier restrictions make repeatable evaluation of discovery, scoring, edge-case handling, and deduplication difficult without a deterministic baseline.

This pack enables:
1. **Repeatable AI Fit Scoring & Calibration:** Score 20 realistic X candidate profiles from `1` to `4` against `scoring_guide.md` and compare your LLM scorer's output against X-Scout AI Partners' human scores in `fund_reference_scores.csv`.
2. **Evidence-Grounded DM Generation:** Verify that every drafted DM cites concrete evidence (`post_id`, repo name, paper, or project from `recent_posts`) without inventing fake familiarity.
3. **Edge-Case & Guardrail Verification ("What must be true"):**
   - **Deduplication (`P001`, `P004`, `P020`):** Profiles already present in `outreach_history_log.csv` or submitted twice with the same `x_user_id` must never be double-messaged.
   - **Prompt Injection Defense (`P017`):** Profile bio and posts contain adversarial instructions attempting to hijack the scorer and DM generator.
   - **Insufficient Evidence / Anti-Hallucination (`P018`):** Sparse profile with no substantive bio or AI/Robotics posts; must be flagged as `needs_a_person` / `insufficient_evidence` rather than hallucinating accomplishments.
   - **Blocked Action – Closed DMs (`P019`):** High-fit founder profile where `can_dm: false`; system must surface a clear `dm_closed` blocked state rather than failing silently or marking as `sent`.

---

## Files in This Pack

| File / Folder | What it contains |
| :--- | :--- |
| `scoring_guide.md` | The **1-to-4 Fit Scoring Rubric** across X-Scout AI's target domains (AI Models, Applications, DevTools, Infrastructure, Robotics/Embodied AI) and strict **Grounded DM Drafting Rules**. |
| `profiles/` | **20 candidate X profiles (`P001.json` – `P020.json`)**. Each JSON file holds one X user's metadata, bio, DM availability (`can_dm`), seed source, and recent posts. |
| `fund_reference_scores.csv` | Reference scores (`1` to `4`) assigned by X-Scout AI's Investment Partner & Scouting Lead for 12 profiles in `profiles/`, used to benchmark AI scoring alignment. |
| `outreach_history_log.csv` | Historical outreach log showing prior DMs sent by the fund, delivery status, whether the recipient replied (`replied`), and whether follow-up attention is needed (`needs_attention`). |
| `seed_segments.csv` | Target segments and seed accounts used by X-Scout AI to discover AI and Robotics builders across Southeast Asia. |

---

## Data Dictionary

### 1. `profiles/*.json`
- `profile_id`: Pack identifier (`P001` to `P020`).
- `x_user_id`: Immutable X numeric user ID string (primary key for deduplication).
- `handle`: X username (without `@`).
- `display_name`: User's public name on X.
- `location`: Self-reported location string.
- `bio`: User's profile description on X.
- `url`: External link (GitHub, lab page, company site, or `null`).
- `followers_count` / `following_count`: Social graph metrics.
- `can_dm`: Boolean indicating whether the user's X privacy settings allow incoming Direct Messages.
- `discovered_via`: Which seed account or target segment query surfaced this profile.
- `recent_posts`: Array of recent X posts (`post_id`, `created_at`, `text`, `metrics`).

### 2. `outreach_history_log.csv`
- `outreach_id`: Unique log identifier (`OUT-101`, etc.).
- `profile_id`: Matches `profile_id` in `profiles/` (if in current batch).
- `x_user_id`: Immutable X numeric user ID.
- `handle`: X username.
- `status`: Current pipeline state:
  - `sent`: DM was delivered; awaiting recipient response.
  - `replied`: Recipient replied to our DM.
  - `blocked_dm_closed`: Attempted outreach blocked because recipient has DMs closed.
- `needs_attention`: `true` if the recipient replied with a question/interest or requires partner follow-up; `false` otherwise.
- `sent_at`: ISO-8601 timestamp when the initial DM was sent.
- `sent_message`: Exact text of the DM sent from X-Scout AI's account.
- `last_reply_at`: ISO-8601 timestamp of the recipient's reply (empty if no reply).
- `last_reply_text`: Text of the recipient's reply (empty if no reply).

You may add your own test profiles or live-fetched X profiles alongside these files.

