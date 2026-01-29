# Chat Summary (2026-01-28)

## Context
- Goal: agent listens to negotiations and detects tactics (anchoring, authority, urgency, framing) using Deepgram + OpenAI LLM.
- Test setup: YouTube audio, mic input; later iPhone YouTube playback near computer mic.

## Key findings from code review
- Speaker mapping fixed: backend now passes raw Deepgram speaker IDs; Coach maps to USER/COUNTERPARTY.
- Live advice requires selecting **Live Companion Mode** in overlay.
- Deepgram originally only emitted `speech_final` → terminal updates only on pauses.

## Changes applied
1) **Enable interim results & continuous logging**
   - Added `interim_results=true` to Deepgram URL.
   - Log `is_final` (Intermediate Final) at INFO for near-continuous terminal output.
   - File: `backend/services/audio_processor.py`

2) **Toggle to forward interim results to LLM**
   - AudioProcessor now supports `emit_interim` flag (env `DG_EMIT_INTERIM` or config) and forwards intermediate finals to callback when enabled.
   - Added config wiring in `backend/main.py`.
   - Added UI checkbox “Continuous LLM updates” in PreFlight and plumbed to backend.
   - Files: `backend/services/audio_processor.py`, `backend/main.py`, `frontend/src/PreFlight.tsx`, `frontend/src/Overlay.tsx`

## Current guidance for testing
- For continuous terminal text: enable **Continuous LLM updates**.
- For live suggestions: enable **Live Companion Mode**.
- For YouTube testing: keep **Test Mode (YouTube)** ON (treats all audio as COUNTERPARTY).

## Suggested overlay selections (current test)
- Live Companion Mode: ON
- Continuous LLM updates: ON
- Test Mode (YouTube): ON

## Open items / optional future improvements
- UI advice parsing still expects newline text; backend sends JSON. (Not addressed yet.)
- Mic-only mixing still halves amplitude; can be fixed if needed.
- If desired: add on-screen indicator for streaming mode; add backend audio level logs.

## Latest user status
- Improvements worked well.
- User will continue testing (iPhone YouTube playback) and hasn’t requested further changes yet.
