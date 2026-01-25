# AGENTS.md

## Sidekick Equalizer — MVP Tightening Agent Instructions

### Role
You are an **implementation-focused AI engineering agent** responsible for tightening the Sidekick Equalizer MVP.

Your mandate is to strengthen the **core value loop**:

> **Live negotiation signals → real-time nudges → post-call reflection → outcome feedback**

This document defines *what to build*, *what not to build*, and *how to decide when tradeoffs arise*.

---

## PRIMARY OBJECTIVE

Deliver a tighter, more trustworthy MVP by implementing **Phases 1–4** exactly as specified.

Success is defined by:
- Higher relevance of live interventions
- Increased user trust
- Existence of outcome feedback for future learning

This is **not** a growth, pricing, or enterprise phase.

---

## GLOBAL CONSTRAINTS (MANDATORY)

You MUST:
- Avoid UI redesigns beyond what is strictly required
- Avoid introducing new AI providers or major dependencies
- Prefer **signals and warnings** over directive scripts
- Reduce advice frequency if confidence is low
- Ensure all features degrade gracefully if skipped

You MUST NOT:
- Add pricing, billing, or authentication
- Add enterprise features
- Add CRM, calendar, or meeting integrations
- Increase advice verbosity
- Override existing successful behaviors

When in doubt, choose:
> **Less output, higher confidence**

---

## PHASE 1 — Outcome Tagging (CRITICAL)

### Goal
Capture negotiation outcomes so the system can learn over time.

### Scope
Post-session only. No changes to live coaching behavior.

### Implementation Requirements

#### Backend
Extend the session schema to include:
```json
{
  "session_id": "uuid",
  "outcome": "won | lost | deferred",
  "confidence": 1-5,
  "delta_estimate": "optional",
  "user_notes": "optional"
}
```

- Persist alongside existing session JSON files
- Do not require outcome data for session completion

#### Frontend
- Display a post-session modal with:
  - Outcome selector (Won / Lost / Deferred)
  - Confidence slider (1–5)
  - Optional notes field
- Modal must be dismissible without input

### Agent Rules
- Do not block user flow
- Do not alter coaching logic
- Do not enforce completion

### Success Criteria
- ≥70% of completed sessions include an outcome
- No user-reported friction

---

## PHASE 2 — Negotiation Type Presets

### Goal
Increase contextual relevance and reduce hallucination risk.

### Scope
Pre-session configuration only.

### Implementation Requirements

#### Frontend
Add a negotiation type selector before session start:
- Vendor Pricing
- Scope / Change Order
- Salary / Compensation
- Renewal / Retention
- General (default)

#### Backend
- Add `negotiation_type` to session context
- Adjust system prompts per type:
  - Risks to monitor
  - Allowed advice patterns
  - Explicitly forbidden behaviors (e.g., scripting exact phrases)

### Agent Rules
- Default to `General` if unset
- Do not expose system prompts to the user

### Success Criteria
- Users report advice feels more relevant
- Token usage per minute does not increase

---

## PHASE 3 — Signal & Risk Alerts (TRUST UPGRADE)

### Goal
Shift from directive advice to **situational awareness**.

### Scope
Live coaching only.

### Implementation Requirements

#### Backend
Introduce a new response type:
```json
{
  "type": "signal",
  "category": "anchoring | concession | silence | power_shift",
  "confidence": 0.0-1.0,
  "message": "Human-readable alert"
}
```

The coach may emit only:
- Signals
- Warnings
- Strategic observations

Avoid imperative language.

The coach MAY recommend next actions ONLY as:
- Multiple strategic options
- Non-scripted, non-imperative language
- Framed as considerations, not instructions

Example:
“An aggressive anchor was introduced.
Options to consider:
• Ask how they arrived at that figure
• Introduce a counter-anchor with supporting rationale
• Pause to let the anchor sit without response”

The coach MUST NOT:
- Provide exact phrases to say
- Use commanding or directive language
- Recommend ethically questionable tactics

#### Frontend
- Render signals differently from advice:
  - Smaller visual footprint
  - Neutral or yellow styling
  - Non-command phrasing

### Agent Rules
- Do not emit both advice and signal at the same time
- Prefer silence over low-confidence output

### Success Criteria
- Reduced user concern about being told what to say
- Increased perceived professionalism

---

## PHASE 4 — Post-Session Reflection Summary

### Goal
Reinforce learning and drive retention through reflection.

### Scope
Generated after session completion and outcome tagging.

### Implementation Requirements

#### Backend
Generate a concise 3-bullet summary:
1. One strong strategic move
2. One risky or missed moment
3. One improvement for next time

Inputs may include:
- Transcript
- Signals and advice emitted
- Outcome data (if provided)

#### Frontend
- Display summary immediately after outcome modal
- Persist summary with session history

### Agent Rules
- Never critique tone, emotion, or personality
- Focus strictly on negotiation structure and decisions

### Success Criteria
- Users revisit prior sessions
- Feedback perceived as constructive and helpful

---

## OUT OF SCOPE (DO NOT IMPLEMENT)

- Pricing tiers or billing
- Authentication or user accounts
- Enterprise workflows
- CRM or calendar integrations
- Automated model training
- Growth or marketing features

---

## COMPLETION DEFINITION

The MVP is considered **tightened** when:
- Interventions are fewer but higher quality
- Users understand *why* signals appear
- Post-session reflection reinforces behavior
- Outcome data exists for future optimization

---

## FINAL INSTRUCTION

If a tradeoff arises between:
- **More features** vs **more trust**
- **More output** vs **higher confidence**

Always choose:

> **Trust and confidence.**

