# Sidekick Equalizer Post-MVP Implementation Plan

## 🎯 Goal
Refine and tighten the MVP to increase user trust, relevance, and learning value. The focus shifts from "more features" to "higher quality signals".

---

## 📋 Feature Prioritization (Revised)

| Priority | Feature | Complexity | Status |
|----------|---------|------------|--------|
| **Phase 1** | Outcome Tagging | Low | ✅ Complete |
| **Phase 2** | Negotiation Presets | Medium | ✅ Complete |
| **Phase 3** | Signal & Risk Alerts | High | ✅ Complete |
| **Phase 4** | Reflection Summary | Medium | ✅ Complete |

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
- **Scope**: Focus on creep, timeline pressure
- **Renewal**: Focus on policy pressure, lock-in
- **General**: Balanced coaching
- **Salary**: Focus on market value, benefits (backend type; not exposed in current UI)

### Frontend
- Add "Pre-Flight" screen before session start
- Selector for: Vendor, Scope, Renewal, General (Salary is currently hidden in UI)

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
    "options": ["Consider asking for rationale", "One option is to pause briefly", "Another approach could be to counter-anchor"]
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

---

## Phase 5: Refactor & Privacy Hardening (Current / In-Progress)
**Goal:** strict separation of concerns, transparency, and "Debrief First" architecture.

### Backend
- **Core Engine Extraction:** Separate intelligence from UI/State.
- **Mode Enforcement:**
  - **Debrief (Default):** No live signals. 100% passive.
  - **Live (Opt-in):** Explicit user consent required for real-time advice.
- **Privacy:** Ensure local-first data handling.

### Frontend
- **Mode Selection:** Explicit preset choice (Practice / Live Call / Post Negotiation Analysis Only).
- **Visual Status:** Clear indicators of current mode.

---

## Phase 5.5: Experience Polish (Immediate Next Steps)
**Goal:** Fix high-friction UX issues discovered during validation (fragile speaker ID, missing history).

### 1. Session History Dashboard
- **Problem:** Report cards disappear after session end.
- **Solution:** "Past Sessions" view in Pre-Flight screen to review previous scores and transcripts.
- **Tech:** Read from local `sessions/*.json` files.

### 2. Speaker Identification Safety Net
- **Problem:** "User Must Speak First" is fragile; one mistake ruins the analysis.
- **Solution:** "Swap Speakers" toggle in the Report Card view to re-run analysis with inverted IDs.

### 3. Latency & Overlap Tuning
- **Problem:** Fast interruptions cause missed tactics (Intermediate results dropped).
- **Solution:** Tune VAD endpointing and queue logic to capture rapid-fire turns.

---

## Future Roadmap (Post-Refactor)

### Phase 6: Local Inference Engine (Privacy ++)
**Goal:** Remove dependencies on cloud APIs (OpenAI) for core tactic detection.
- **Implementation:** Migrate `tactic_detection.py` to use local `Llama-3-8B-Quantized` via `llama.cpp` or `Ollama`.
- **Benefit:** 100% offline, zero data leakage, lower cost.

### Phase 7: Latency Reduction (Voice-to-Voice)
**Goal:** Sub-500ms latency for seamless assistance.
- **Implementation:**
  - Local STT (Whisper tiny/base).
  - Local TTS (Coqui or similar) for audio cues (optional).
  - WebSockets optimization (binary streams).

### Phase 8: Custom Tactic Training
**Goal:** Allow users to define their own specific signals.
- **Implementation:**
  - JSON configuration for "Trigger Phrases" (e.g. "We don't have budget").
  - User-defined response signals.

### Phase 9: Multi-Party Role Assignment ("Friend or Foe")
**Goal:** Handle complex negotiations with multiple speakers on each side (e.g., Legal Counsel, Technical Experts).
- **Implementation:**
  - **Diarization Map:** UI to visualize detected speakers (Speaker 0, 1, 2, 3...).
  - **Role Toggle:** User can label each speaker ID as "Ally" (Ignore) or "Opponent" (Analyze).
  - **Impact:** Prevents own team members from triggering "Authority" or "Risk" alerts.
