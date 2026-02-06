# Sidekick Equalizer

**Sidekick Equalizer** is a real-time AI negotiation coach that sits as a transparent, draggable overlay on your screen. It listens to your negotiation (via microphone) and provides instant, tactical advice to help you level the playing field.

## 🏗️ Architecture

```
┌─────────────┐     Audio      ┌─────────────┐
│   Electron  │ ──────────────▶│   FastAPI   │
│   Overlay   │    WebSocket   │   Backend   │
└─────────────┘                └──────┬──────┘
                                      │
                                      ▼
                               ┌─────────────┐
                               │ Core Engine │◀─── New!
                               │  (Logic)    │
                               └──────┬──────┘
                                      │
                                      ▼
                               ┌─────────────┐
                               │  Coach AI   │
                               │ (GPT-4o-mini)│
                               └─────────────┘
```

**Tech Stack:**
- **Frontend**: Electron + React (TypeScript) — Draggable floating HUD
- **Backend**: Python FastAPI — WebSocket server + AI pipeline
- **Core Engine**: Pure Python logic for tactic detection & signal gating
- **Role Mapping**: Strict `User` (Speaker 0) vs `Counterparty` (Speaker 1+) enforcement, with optional Test Mode override for demos
- **AI**: Deepgram Nova-2 (Streaming STT) + OpenAI GPT-4o-mini (Coach)

---

## 🚀 Getting Started

### 1. Prerequisites
- **Node.js**: v18+
- **Python**: 3.10+ (recommend using `conda`)
- **Deepgram API Key**: [Get one here](https://console.deepgram.com/)
- **OpenAI API Key**: [Get one here](https://platform.openai.com/)

### 2. Configure Environment
Create a `.env` file in `backend/`:
```bash
cd backend
cp .env.example .env
```
Add your keys:
```ini
OPENAI_API_KEY=sk-your-key-here
DEEPGRAM_API_KEY=your-deepgram-key-here
```

### 3. Installation

**Backend:**
```bash
cd backend
conda activate ai
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

---

## ▶️ How to Run

Open **two terminals**:

**Terminal 1: Backend**
```bash
cd backend && conda activate ai && python main.py
```
*You should see: `Uvicorn running on http://127.0.0.1:8000`*

**Terminal 2: Frontend**
```bash
cd frontend && npm run electron:dev
```
*A draggable green overlay window will appear.*

---

## 🎮 Usage Guide

### Product Modes (Presets)
The system uses three presets in the **Pre-Flight** screen:

1. **Practice Mode**
   - Live analysis + Test Mode + Continuous updates.
   - Ideal for self-training and demos.
   - **Note:** Ignores speaker gating (analyzes *all* audio).
2. **Live Call**
   - Live analysis with strict gating.
   - Only analyzes audio detected as **Counterparty** (Speaker 1+).
   - **Requirement:** User (Speaker 0) MUST speak first to establish identity.
3. **Post Negotiation Analysis Only**
   - No live popups.
   - Records session silently.
   - Generates a comprehensive "Report Card" at the end.

### Standard Flow
1. **Select Scenario:** Vendor, Scope, Renewal, General.
2. **Select Mode:** Practice Mode / Live Call / Post Negotiation Analysis Only.
3. **Initialize:** Overlay appears in "LISTENING" state.
   > **CRITICAL:** Ensure YOU (the User) speak the first sentence to lock in "Speaker 0" identity.
4. **Negotiate:** 
   - In **Live/Practice**, watch for "⚠️ SIGNAL" alerts.
5. **End Session:** Click Stop -> Save Outcome (Won/Lost) -> Check "Include Expanded Debrief".
6. **Report Card:** Review the detailed breakdown:
   - **Score:** 0-100 Performance Rating.
   - **Tactics Faced:** List of specific tactics used against you (e.g., "ANCHORING: Seller asked for $125k").
   - **Key Moments:** Coaching on your "Strongest Move" and "Missed Opportunities".

### Supported Tactics (Detection Engine v2)
The "Hybrid" engine combines real-time signal detection with LLM synthesis to identify:
- **Anchoring:** numeric_anchor, range_anchor, comparison_anchor
- **Urgency:** deadline, scarcity
- **Authority:** manager_deferral, policy_shield
- **Framing:** roi_reframe, monthly_breakdown, minimization
- **Commitment Traps:** conditional_commitment, reciprocity_gate
- **Concessions:** staged_concession, tradeoff_offer
- **Bundling:** add_on_bundle, take_it_or_leave_it_package
- **Payment Deflection:** monthly_focus, affordability_frame
- **Loss Aversion:** fear_of_missing_out, loss_warning
- **Social Proof:** popularity_claim, herd_reference

### Session History Dashboard
- Access past negotiation reports by clicking the **"History"** button in Pre-Flight or Main Overlay.
- View stats at a glance: Date, Scenario, Duration, Score, and Outcome.
- Click any session to replay the detailed "Report Card" analysis.

---

### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+S` | Toggle pause/resume listening |
| `Ctrl+Shift+E` | End Session & Generate Report |

---

## ✅ Verification & Testing

### Live Simulation (Backend Only)
Test the analysis engine without the frontend or microphone:
```bash
cd backend
python scripts/simulate_live.py
```
*This simulates a conversation with "User" and "Counterparty" lines to trigger tactics.*

### Unit Tests
Run the test suite (including new Role Mapping tests):
```bash
PYTHONPATH=/home/robert/Coding/equalizer/backend pytest backend/tests
```

---

## 📁 Project Structure

```
equalizer/
├── backend/
│   ├── core/                # pure logic (no web/db dependencies)
│   │   └── analysis_engine/ # tactic detection & schemas
│   ├── main.py              # FastAPI WebSocket server
│   ├── services/
│   │   ├── audio_processor.py
│   │   ├── coach.py         # Orchestrator (delegates to Core)
│   │   └── session_recorder.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── PreFlight.tsx    # Mode & Scenario selection
│   │   ├── Overlay.tsx      # Main HUD
│   │   └── ...
├── sessions/                # Local JSON recordings
├── agents.md                # Behavioral instructions
└── uat.md                   # User Acceptance Tests
```

---

## 🔮 Roadmap
See [docs/POST_MVP_ROADMAP.md](docs/POST_MVP_ROADMAP.md) for details on:
- **Phase 6:** Local Inference (Llama 3)
- **Phase 7:** Latency Reduction
