# Sidekick Equalizer

**Sidekick Equalizer** is a real-time AI negotiation coach that sits as a transparent, draggable overlay on your screen. It listens to your negotiation (via microphone) and provides instant, tactical advice to help you level the playing field.

## 🏗️ Architecture

```
┌─────────────┐     Audio      ┌─────────────┐
│   Electron  │ ──────────────▶│   FastAPI   │
│   Overlay   │    WebSocket   │   Backend   │
└─────────────┘                └──────┬──────┘
       ▲                              │
       │ Advice                       ▼
       │                       ┌─────────────┐
       └───────────────────────│  Deepgram   │
                               │  Nova-2 STT │
                               └──────┬──────┘
                                      │ Transcript
                                      ▼
                               ┌─────────────┐
                               │  Coach AI   │
                               │ (GPT-4o-mini)│
                               └─────────────┘
```

**Tech Stack:**
- **Frontend**: Electron + React (TypeScript) — Draggable floating HUD
- **Backend**: Python FastAPI — WebSocket server + AI pipeline
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

1. **Drag the overlay** to position it near your Zoom/Teams window
2. **Speak into your microphone** — The app listens in real-time
3. **Watch for advice** — A green card appears when tactical advice is warranted
   - Example: *"Don't accept yet. Ask for their best price first."*
4. **Auto-dismiss** — Advice vanishes after 8 seconds

### Status Indicators
| Status | Meaning |
|--------|---------|
| 🎤 LISTENING... | Connected and monitoring audio |
| ⏳ CONNECTING... | Attempting to connect to backend |
| ⚠️ CONNECTION ERROR | Backend not running or unreachable |

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| **Connection Error** | Ensure backend is running on port 8000 |
| **No advice appearing** | Check backend logs — if "Advice NOT warranted", AI is choosing silence (working as designed) |
| **No transcripts in logs** | Check microphone permissions in OS settings |
| **Overlay not on top** | Avoid full-screen apps; use windowed mode for presentations |
| **Electron sandbox error (Linux)** | Run with `--no-sandbox` flag (already configured) |

---

## 📁 Project Structure

```
equalizer/
├── backend/
│   ├── main.py              # FastAPI WebSocket server
│   ├── services/
│   │   ├── audio_processor.py  # Deepgram WebSocket client
│   │   └── coach.py            # GPT-4o-mini advisor logic
│   ├── .env                 # API keys (not in git)
│   └── requirements.txt
├── frontend/
│   ├── electron/
│   │   └── main.js          # Electron window config
│   ├── src/
│   │   ├── App.tsx          # React app root
│   │   └── Overlay.tsx      # Main overlay component
│   └── package.json
├── agents.md                # AI personality definitions
└── README.md
```

---

## 🔮 Future Enhancements

See [docs/POST_MVP_ROADMAP.md](docs/POST_MVP_ROADMAP.md) for detailed implementation plans.

**Completed:**
- [x] Keyboard shortcut to toggle listening (Ctrl+Shift+S)
- [x] Persist overlay position across sessions

**Upcoming:**
- [ ] Custom Coach personalities (aggressive vs. diplomatic)
- [ ] Capture system audio (hear both sides of call)
