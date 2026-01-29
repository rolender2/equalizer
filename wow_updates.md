# WOW_UPDATES.md
Project: Sidekick Equalizer (MVP)
Audience: AI Coding Agent (Codex / Cursor / Copilot)
Goal: Add high-impact “wow” features for demo readiness **without changing core architecture or product philosophy**.

---

## Product Intent (Read First)

This product is an **assistive negotiation sidekick**, not a chatbot negotiator.

DO NOT:
- Script the user
- Tell the user what to say verbatim
- Generate aggressive or seller-side persuasion
- Increase system chatter or constant alerts

DO:
- Detect negotiation pressure
- Explain *why it matters*
- Offer calm, buyer-side options
- Suggest one high-quality “next question”

Silence is preferred to low-confidence noise.

---

# SCOPE OF THIS UPDATE

You are implementing **WOW FACTORS**, not a redesign.

Core pipeline remains:
Audio → Transcription → Segmentation → Detection → Advice → Overlay

---

# STEP 1 — Live Advice Payload v3 (HIGH PRIORITY)

### Objective
Replace “ANCHORING detected” with a **structured insight** that feels intelligent and helpful.

### Backend Output Schema (single event)
Emit **one** object per window, or nothing.

```json
{
  "category": "ANCHORING | URGENCY | AUTHORITY | FRAMING | NONE",
  "subtype": "numeric_anchor | range_anchor | comparison_anchor | deadline | scarcity | manager_deferral | policy_shield | roi_reframe | monthly_breakdown | minimization | none",
  "confidence": 0.0,
  "headline": "Pricing Anchor Set",
  "why": "First numbers tend to pull the negotiation toward them.",
  "best_question": "What assumptions are baked into that number?",
  "options": [
    "Consider asking for a breakdown of how that figure was calculated.",
    "One option is to pause and request external benchmarks before responding.",
    "Another approach could be to introduce an alternative reference point."
  ],
  "evidence": "Exact quote from transcript",
  "timestamp": "segment timestamp"
}
