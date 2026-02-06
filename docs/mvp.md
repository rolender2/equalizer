# Sidekick Equalizer MVP Overview

**Version:** 1.0.0 (MVP Tightening Complete)
**Status:** ✅ Production Ready for Desktop

## 🎯 Product Vision
Sidekick Equalizer is a **real-time desktop negotiation companion** designed to level the playing field for individuals against AI-armed enterprises and professional negotiators.

Unlike passive call recorders, Sidekick provides **active, privacy-first coaching** during high-stakes conversations (Vendor Contracts, Renewals, Scope Changes). It doesn't just record; it **thinks** and **signals** tactical opportunities in real-time.

---

## 🌟 Core MVP Features

### 1. Real-Time "Co-Pilot" Overlay
- **Technology:** Electron + React (Transparent, draggable overlay)
- **Function:** Floats over Zoom/Teams/Meet.
- **Privacy:** "Toggle-to-Listen" architecture (not always-on). User explicitly activates it for specific calls.
- **Visuals:** Minimalist HUD that stays out of the way until it detects a signal.

### 2. High-Stakes Presets (Context Awareness)
Before a call, the user selects a specific "Flight Mode" to prime the AI:
- **🏢 Vendor:** Alerts on "standard inflation" excuses and anchors.
- **🔭 Scope:** Prevents scope creep and uncompensated asks.
- **🔄 Renewal:** Spots "policy" bluffs and "lock-in" tactics.
- **🌐 General:** Balanced coaching for everyday disputes.
*Note: Salary exists in backend negotiation types but is not currently exposed in the UI preset list.*

### 3. Tactical Signal Detection (Counter-AI)
Instead of generic advice, the system identifies specific **Persuasion Tactics** used by the counterparty:
- **Anchoring:** "High anchor detected ($50k). Consider asking for a rationale or benchmark."
- **False Urgency:** "Scarcity tactic detected. Consider verifying if the deadline is real."
- **Authority / Policy Shield:** "They are deferring to a 'manager' or policy."
- **Output:** Structured "Signal" + 3 Strategic Options (not commands).

### 4. Outcome Tagging & Learning Loop
Post-session data capture to track personal performance:
- **Result:** WON / LOST / DEFERRED
- **Confidence Score:** 1-5 rating of user performace.
- **Notes:** Structured takeaways.
- **Data Storage:** Local JSON files (Privacy-first).

### 5. Immediate Reflection (Debrief)
Instantly after a session, the AI generates a "Game Tape" analysis:
- ✅ **Strong Move:** Positive reinforcement of a good tactic used.
- ⚠️ **Missed Opportunity:** A moment where leverage was lost.
- 💡 **Improvement Tip:** Concrete action for the next negotiation.

---

## 🏗️ Technical Implementation
- **Frontend:** Electron/React (Desktop Native)
- **Backend:** Python FastAPI (Local Server)
- **Speech-to-Text:** Deepgram Nova-2 (Streaming, <300ms latency)
- **Intelligence:** OpenAI GPT-4o-mini (Cost-optimized, Low-latency)
- **Audio:** Custom Diarization & System Audio Capture (Loopback)

## 🛡️ Privacy & Trust
- **Local-First:** System is designed to run locally; audio streams go to STT provider (ephemeral) but core logic is controlled by the user.
- **Consent:** Explicit "Start/Stop" control. No hidden background recording.
- **Transparency:** Clear UI indicators when "Listening".

## 🚀 Next Steps (Post-MVP)
- **Export/Review UI:** A dedicated dashboard to review past session JSONs.
- **CRM Integration:** Sync outcomes to HubSpot/Salesforce (B2B focus).
- **Custom Playbooks:** Allow users to define their own signals.
