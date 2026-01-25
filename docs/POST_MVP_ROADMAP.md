# Sidekick Equalizer Post-MVP Implementation Plan

## 🎯 Goal
Refine and tighten the MVP to increase user trust, relevance, and learning value. The focus shifts from "more features" to "higher quality signals".

---

## 📋 Feature Prioritization (Revised)

| Priority | Feature | Complexity | Status |
|----------|---------|------------|--------|
| **Phase 1** | Outcome Tagging | Low | ❌ Pending |
| **Phase 2** | Negotiation Presets | Medium | ❌ Pending |
| **Phase 3** | Signal & Risk Alerts | High | ❌ Pending |
| **Phase 4** | Reflection Summary | Medium | ❌ Pending |

---

## Phase 1: Outcome Tagging (CRITICAL)
**Goal:** Capture negotiation results (Won/Lost/Deferred) to enable future learning.

### Backend
- Update `SessionRecorder` to accept outcome data `{result, confidence, notes}`
- Include `negotiation_type` (sourced from session context) in outcome data
- Add `POST /sessions/{id}/outcome` endpoint

### Frontend
- Create `OutcomeModal` component
- Trigger modal on session end
- Simple inputs: Won/Lost/Deferred, Confidence (1-5), Notes

---

## Phase 2: Negotiation Presets
**Goal:** Increase advice relevance context.

### Backend
- **Shared Base Prompt Architecture**: All types inherit from base.
- Type-specific overrides limited to: Risk focus & Option framing.
- **Vendor Pricing**: Focus on savings, anchoring
- **Salary**: Focus on market value, benefits
  - **General** (Balanced)

### Frontend
- Add "Pre-Flight" screen before session start
- Selector for: Vendor, Scope, Salary, Renewal, General

---

## Phase 3: Signal & Risk Alerts (Trust Upgrade)
**Goal:** Shift from "Backseat Driver" to "Co-Pilot Radar" with Strategic Options.

### Backend
- Coach outputs structured signals with multiple options:
  ```json
  { 
    "type": "signal", 
    "category": "anchoring", 
    "message": "High anchor detected",
    "options": ["Ask for rationale", "Use silence", "Counter-anchor"]
  }
  ```
- **Strict Rule:** No imperative/command language.
- **Confidence Gate:** Output options ONLY if confidence ≥ 0.7. Else silent.

### Frontend
- UI displays the Signal (Awareness) + bulleted Options (Strategy)
- Replaces the single "Big Green Text" advice style

---

## Phase 4: Post-Session Reflection
**Goal:** Reinforce learning immediately after the call.

### Backend
- Generate 3-bullet summary: 1 Strong Move, 1 Missed Opportunity, 1 Fix
- Call LLM with full transcript + outcome

### Frontend
- Display summary immediately after Outcome Modal
- Persist summary with session history

---

## OUT OF SCOPE
- Enterprise features / Auth / Billing
- CRM Integrations
- Automated model training
