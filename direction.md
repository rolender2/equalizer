# AGENTS.md

## Purpose

This document defines **non-negotiable architectural and behavioral instructions** for all AI coding agents contributing to the Sidekick Equalizer codebase.

The objective of this refactor is **not feature expansion**, but **architectural tightening** to align the product with validated market realities while preserving the long-term vision.

Agents must treat this document as the highest-priority instruction set.

---

## Core Product Principle

> **Sidekick Equalizer is a Personal Conversation Intelligence System, not a script engine.**

The system exists to:

* Detect persuasion and negotiation tactics
* Explain why they matter
* Surface strategic options
* Preserve human agency at all times

The system must NEVER:

* Issue commands
* Provide scripts to read verbatim
* Simulate or impersonate a human speaker

---

## Refactor Objectives (Critical)

Agents must execute the refactor with the following outcomes:

1. **Separate intelligence from interface**
2. **Make post-call analysis a first-class product path**
3. **Downgrade real-time coaching to an optional advanced mode**
4. **Preserve privacy-first, local-first design**
5. **Reduce coupling and cognitive load**

If a proposed change violates any of the above, it must not be implemented.

---

## Required Architectural Changes

### 1. Extract Core Analysis Engine (MANDATORY)

All negotiation intelligence must live in a UI-agnostic core module.

#### Create or refactor into:

```
/core
  /analysis_engine
    tactic_detection.py
    confidence_scoring.py
    coaching_generation.py
    schemas.py
```

#### Rules

* No UI code may contain tactic logic
* No UI code may call LLMs directly
* The core engine must accept transcripts as input and return structured JSON

#### Required Core Inputs

```python
TranscriptSegment:
  speaker: str
  timestamp: float
  text: str
```

#### Required Core Outputs

```json
{
  "signals": [
    {
      "tactic": "ANCHORING | URGENCY | AUTHORITY | FRAMING",
      "confidence": 0.0-1.0,
      "evidence": "string",
      "timestamp": "float",
      "options": ["string", "string", "string"]
    }
  ],
  "summary": {
    "strong_move": "string",
    "missed_opportunity": "string",
    "improvement_tip": "string"
  }
}
```

The engine must never emit imperative language.

---

### 2. Establish Two Explicit Product Modes

The system must support **two modes**, with clear separation:

#### 🧠 Debrief Mode (DEFAULT)

* Post-call analysis only
* Full transcript processed at once
* Produces scorecard, detected tactics, and coaching summary
* This is the **primary MVP experience**

#### ✈️ Live Companion Mode (ADVANCED)

* Optional, explicitly enabled
* Consumes transcript windows (not full streaming)
* Emits signals only when confidence exceeds threshold
* Uses the same core engine

Real-time logic must be thin and defer to the core engine.

---

### 3. Refactor Real-Time Flow (DE-RISKING)

Agents must modify the existing real-time implementation so that:

* Analysis occurs in **time windows** (e.g. every 15–30 seconds)
* Signals are emitted only if confidence >= configured threshold
* Silence is preferred over low-confidence alerts

The UI must show:

* "Signal Detected" (what)
* "Why it matters" (context)
* "Options to consider" (2–3 max)

No commands. No scripts.

---

### 4. Promote Post-Call Analysis to First-Class Flow

Agents must implement a complete post-call pipeline:

```
Audio Input
 → Transcription
 → Core Analysis Engine
 → Outcome Tagging
 → Coaching Summary
```

This flow must work **without** any real-time components.

---

## Outcome Tagging & Learning Loop (RETAIN)

Outcome tagging is a strategic asset and must be preserved.

### Required Fields

```json
{
  "result": "won | lost | deferred",
  "confidence": 1-5,
  "notes": "string"
}
```

Rules:

* Outcome data attaches to a session
* Stored locally by default
* Never used to auto-train models without explicit user consent

---

## Prompting Rules (STRICT)

All LLM prompts must:

* Use structured output (JSON)
* Avoid imperative verbs
* Avoid certainty unless confidence is high
* Cap options at 3

Forbidden phrases:

* "You should say"
* "Do this now"
* "Tell them"

Allowed framing:

* "A possible interpretation is…"
* "One option to consider…"
* "You may want to evaluate…"

---

## Privacy & Trust Constraints

Agents must preserve the following guarantees:

* Explicit user-initiated listening only
* Clear on/off indicators
* Local-first storage
* Ephemeral audio wherever possible
* Transparent data flows

No background listening. No covert capture.

---

## What NOT to Build (IMPORTANT)

Agents must not:

* Add social features
* Add gamification
* Add public sharing
* Add automated responses or scripts
* Add background surveillance features

These are explicitly out of scope for MVP tightening.

---

## Definition of Success

This refactor is successful when:

* The core engine can run headless (no UI)
* Post-call analysis is useful on its own
* Real-time mode is optional, not required
* The system feels calm, credible, and assistive

If the system feels like a "backseat driver," the refactor has failed.

---

## Final Instruction

When in doubt:

> **Favor trust over cleverness. Favor clarity over speed. Favor architecture over features.**

This product wins by being right, not loud.
