Do not add new top-level directories unless explicitly required.
Prefer small patches over refactors. Do not change product behavior unless the instructions explicitly say to.

---

# Sidekick Equalizer — Coding Agent Instructions (MVP / V2)

This repo is a **real-time negotiation companion overlay** (Electron + React) with a local FastAPI backend.
It streams audio → transcribes via Deepgram → analyzes tactics via an LLM → shows a minimal overlay.

Your job as the coding agent:
- Make **small, safe, testable** changes.
- Preserve the **MVP contract**: low distraction, privacy-first controls, live mode is opt-in.
- Keep outputs **structured and predictable**.

---

## 1) Current Architecture (Source of Truth)

### WebSocket contract
- One WebSocket connection = one session.
- Frontend sends:
  1) Initial JSON config message
  2) Binary PCM audio frames (16kHz, 16-bit)
- Backend sends:
  - `session_init` (optional)
  - `advice` events during live sessions (and summary during debrief end)

### Config payload (from frontend)
Fields that are currently supported / expected:
- `negotiation_type` (string)
- `mode`: `"live"` or `"debrief"`
- `personality` (metadata / prompt steering)
- `test_mode_counterparty` (boolean; forces all segments as COUNTERPARTY for YouTube testing)
- `emit_interim` (boolean; enables analysis on Deepgram “intermediate finals”)
- `user_speaker_id` (int; which Deepgram speaker is the user; default 0 if absent)

Notes:
- If `mode=debrief`, live advice must be suppressed by design.
- `emit_interim=true` is used to get continuous transcript flow for testing sources like YouTube.

---

## 2) Audio + Transcription Rules

### Deepgram streaming
- Use Deepgram Nova-2 streaming.
- Diarization enabled (speaker IDs).
- endpointing is configured to produce usable intermediate/final segments.
- When `emit_interim=true`, intermediate-final segments are passed to the Coach (not only speech finals).

### Testing audio sources
- For YouTube testing where both voices are coming from one audio source:
  - Use `test_mode_counterparty=true` so the coach treats everything as COUNTERPARTY.
  - This is a testing convenience; it is not the normal product behavior.

---

## 3) Coach Logic (V2)

### Role mapping
- Coach receives raw Deepgram speaker IDs (ints).
- Coach maps to roles using:
  - `user_speaker_id` (default 0)
  - `test_mode_counterparty` override (forces all as COUNTERPARTY)

### Modes
- `debrief`: buffer only; no live advice.
- `live`: windowed analysis; produce advice only when warranted.

### Detection strategy (V2)
- Context window: last ~12 segments (context only)
- NEW segment: most recent segment only (the detection target)
- The LLM must prioritize NEW. Context may help disambiguate, but must not override NEW.

### Output contract (IMPORTANT)
- Coach outputs structured JSON advice (not newline text).
- Advice fields must be stable and strict:
  - `category`: ANCHORING | URGENCY | AUTHORITY | FRAMING | NONE
  - `subtype`: one of the project’s supported subtypes
  - `confidence`: 0.0–1.0
  - `message`: short neutral observation
  - `options`: 0–3 neutral, user-protective options (NOT seller-ish)

### Behavioral constraints
- Options must be neutral and user-protective:
  - OK: “Consider asking what happens after today.”
  - NOT OK: “Emphasize the benefits of acting quickly.”
- Avoid imperative commands (“Do X now”), threats, or aggressive language unless the selected personality explicitly calls for it.
- Prefer silence to noise:
  - If low confidence, return `NONE` and do not spam.

### Dedupe / spam control
- Suppress repeated same category/subtype signals for a cooldown period (e.g., 45s).
- If advice was just shown, do not fire again immediately unless a different, stronger signal appears.

---

## 4) Frontend Responsibilities

### PreFlight (before session)
- User selects:
  - Negotiation type
  - Mode (live vs debrief)
  - Test mode (YouTube)
  - Continuous updates (emit_interim)
  - (Optional) user speaker selection if supported
- Defaults must be conservative:
  - Debrief mode recommended by default.

### Overlay (in-call)
- Always-on-top, draggable, minimal.
- Advice card should:
  - Render structured JSON correctly (do not split JSON by newlines).
  - Auto-dismiss after ~8 seconds.
  - Show short: title (mapped from category/subtype), then 0–3 bullets (options).
- Show status indicators (listening / paused / mic+system).

---

## 5) How to Work (Agent Operating Rules)

### Make small patches
- Prefer minimal diff, minimal surface area.
- No “big redesigns” unless requested.

### Do not invent features
- If you propose a feature, confirm it exists in code OR implement it fully with tests.
- If a referenced file doesn’t exist, say so and suggest the simplest correct placement.

### Logging
- Maintain helpful logs in backend for:
  - incoming segments (speaker id + role mapping)
  - analysis windows
  - gating / dedupe decisions
  - final advice payloads

---

## 6) Testing Expectations (Required)

The agent must add or run tests that prove behavior, without building a large harness.

Required checks:
1) WebSocket lifecycle:
   - Connect, send config, stream audio bytes, disconnect cleanly.
2) Mode enforcement:
   - `debrief` never emits live advice.
   - `live` can emit advice when tactics appear.
3) Role mapping:
   - user_speaker_id mapping works.
   - test_mode_counterparty forces all segments to COUNTERPARTY.
4) Advice payload contract:
   - Always valid JSON structure.
   - category/subtype are from allowed sets.
   - options length 0–3, neutral phrasing, no seller-ish phrasing.
5) UI render:
   - Advice JSON displays as a clean card (title + bullets), not as a JSON blob.

Test runner note:
- If you hit `ModuleNotFoundError: services`, run pytest with:
  `PYTHONPATH=/home/robert/Coding/equalizer/backend pytest backend/tests/<test_file>.py`

Optional smoke test:
- YouTube test using `test_mode_counterparty=true` + `emit_interim=true` and verify continuous transcript + periodic advice.

---

## 7) Definition of Done (MVP / V2)

MVP V2 is “done enough to demo” when:
- Overlay stays on top and is non-distracting.
- Audio streaming produces continuous transcripts (especially with emit_interim).
- Live mode produces occasional high-confidence structured advice.
- Debrief mode produces no live advice and supports post-session output.
- Advice presentation looks polished (not raw JSON) and feels helpful.

---

# Final Reminder

This is a product-moment demo:
fast, accurate tactic detection + calm, usable guidance + low distraction.

Ship accordingly.
