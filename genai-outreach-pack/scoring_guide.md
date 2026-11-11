# GenAI Fund – Target Fit Scoring & Grounded DM Guide

Every discovered X profile is evaluated for outreach by **GenAI Fund** (focused on building and backing the AI & Robotics ecosystem in Southeast Asia).

Each profile is scored from **1 to 4** against the rubric below.
- **Pass mark for outreach is 3:** Profiles scored **3 or 4** qualify for personalised DM drafting and review.
- Profiles scored **1 or 2** are archived as low-priority/out-of-scope and should **not** be queued for outreach unless manually overridden by a reviewer.
- Profiles with insufficient public information to verify technical work or draft an evidence-based DM must be marked **`needs_a_person` (`insufficient_evidence`)** rather than guessing a score or fabricating familiarity.

---

## Part 1: Target Domains (What We Care About)

GenAI Fund looks for builders, founders, and researchers actively shipping in one or more of these six tracks:
1. **AI Models (`ai_models`):** Foundation models, domain-specific LLMs, multimodal models, fine-tuning, quantization, SEA-language NLP/speech models.
2. **AI Applications (`ai_applications`):** Vertical AI agents, enterprise AI workflows, production AI products with real users.
3. **Developer Tools (`devtools`):** Agent frameworks, evaluation/observability tools, code-generation tooling, SDKs.
4. **AI Infrastructure (`infrastructure`):** Inference engines, GPU orchestration, vector databases, distributed training, edge deployment runtimes.
5. **Robotics (`robotics`):** Industrial/service/agricultural robots, kinematics, ROS2, hardware-software integration, autonomous navigation, manipulation.
6. **Embodied AI (`embodied_ai`):** Vision-Language-Action (VLA) models, sim-to-real reinforcement learning, humanoid/quadruped policy learning, sensor fusion.

---

## Part 2: The 1-to-4 Fit Scoring Rubric

### Score 1 – Out of Scope / Noise (Do Not Outreach)
- **Who falls here:**
  - General social media influencers, "AI news thread" aggregators ("10 ChatGPT prompts that will blow your mind"), or affiliate marketers.
  - Crypto/Web3 token promoters using "AI" only as a buzzword with no underlying technical artifact.
  - Non-technical roles unrelated to building or researching AI/robotics.
  - Adversarial or spam accounts (including profiles attempting prompt injection).
- **Evidence level:** Zero genuine building or research evidence.

### Score 2 – Weak or Early Signal (Hold / Archive)
- **Who falls here:**
  - General software engineers or students experimenting casually with tutorial-level AI wrappers (e.g., basic chatbot tutorials) without a distinct product, research contribution, or deep technical focus.
  - Tech executives or VCs/consultants who comment on AI trends but are not actively founding, researching, or engineering AI/robotics systems.
- **Evidence level:** Mentions AI/tech generally, but recent posts lack concrete technical depth, shipped artifacts, benchmarks, or research output.

### Score 3 – Strong Fit: Active AI/Robotics Builder or Researcher (Qualifies for Outreach)
- **Who falls here:**
  - Active founders, core engineers, or published researchers building in one of the six target tracks (`ai_models`, `ai_applications`, `devtools`, `infrastructure`, `robotics`, `embodied_ai`).
  - Either based in / connected to Southeast Asia (SEA) **or** building globally relevant open-source/research in our core tracks with clear ecosystem synergy.
- **Evidence level:** Clear, verifiable proof in bio and recent posts (e.g., shipped product update, GitHub repository, benchmark numbers, arXiv preprint, hardware prototype test, or deep technical debugging insight).

### Score 4 – High-Priority Fit: Exceptional SEA Founder / Deep-Tech Leader (Priority Outreach)
- **Who falls here:**
  - Founders, CTOs, or principal researchers directly building deep-tech AI, Infrastructure, DevTools, Robotics, or Embodied AI in **Southeast Asia** (Singapore, Vietnam, Indonesia, Thailand, Malaysia, Philippines) or leading a high-traction venture expanding in SEA.
  - Demonstrates measurable technical execution (e.g., production deployment metrics, open-source traction, peer-reviewed robotics/AI breakthroughs, hardware field trials, or active team scaling).
- **Evidence level:** Multiple concrete data points across bio and recent posts proving both **technical ownership** and **direct SEA ecosystem relevance**.

---

## Part 3: Grounded Personalisation Rules (DM Drafting)

When a profile scores **3 or 4** (or is manually requested for drafting), the system drafts a warm introductory DM from GenAI Fund.

### Mandatory Grounding Rules:
1. **Cite Concrete Evidence Only:**
   - Every draft must reference at least one specific artifact present in the candidate's `recent_posts` or `bio` (e.g., a specific metric they shared, a technical bottleneck they solved, a repository/paper title, or a hardware test).
   - Store the exact `evidence_post_id` and `evidence_quote` alongside the draft so the human reviewer can verify it in one glance.
2. **Zero Invented Familiarity:**
   - Never claim *"We met at [event]"*, *"A mutual friend told me about you"*, or *"I've been following your work for years"* unless explicitly provided in reviewer notes.
   - Avoid hollow flattery (*"Your profile is truly inspiring!"*, *"Love your amazing journey!"*). Speak peer-to-peer.
3. **Clear, Low-Friction Call to Action (CTA):**
   - Introduce GenAI Fund briefly as an AI & Robotics ecosystem builder/investor in Southeast Asia.
   - End with a specific, low-pressure conversation starter related to their work (e.g., asking a technical question about their architecture/rollout, or offering to connect over a quick chat / upcoming SEA builder gathering).
4. **Concise Length:**
   - Keep DMs between **250 and 600 characters** (2–3 short paragraphs). Nobody reads a wall of text in X DMs.

