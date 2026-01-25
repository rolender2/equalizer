# Sidekick Equalizer Post-MVP Implementation Plan

## 🎯 Goal
Evolve Sidekick from MVP to a production-ready negotiation assistant with enhanced audio capture, UX polish, and customization.

---

## 📋 Feature Prioritization

| Priority | Feature | Complexity | Status |
|----------|---------|------------|--------|
| **P1** | System Audio Capture | High | ✅ Complete |
| **P2** | Keyboard Toggle | Low | ✅ Complete |
| **P3** | Position Persistence | Low | ✅ Complete |
| **P4** | Custom Coach Personalities | Medium | ✅ Complete |
| **P5** | Speaker Diarization | Medium | ❌ Pending |

---

## P1: System Audio Capture

> [!IMPORTANT]
> **Critical Feature**: Currently only captures microphone. Need to hear both sides of the call.

### Challenge
- Linux: PulseAudio/PipeWire loopback
- macOS: Requires BlackHole or similar virtual audio device
- Windows: WASAPI loopback

### Proposed Approach
**Option A: Virtual Audio Device (Recommended)**
- User installs BlackHole (macOS) or VB-Cable (Windows)
- Route Zoom output → Virtual device → Sidekick input

**Option B: Add `ffmpeg` system capture**
- Backend spawns `ffmpeg` to capture desktop audio
- Mux with microphone stream

### Implementation
1. Add audio source selector in Electron (microphone vs. system)
2. Create `audio_capture.py` service with platform-specific capture
3. Merge streams before sending to Deepgram

---

## P2: Keyboard Toggle (Mute/Unmute Listening)

### Goal
Press a hotkey to pause/resume audio capture for privacy.

### Implementation

#### [MODIFY] [main.js](file:///home/robert/Coding/equalizer/frontend/electron/main.js)
- Register global shortcut: `Ctrl+Shift+S` (or user-configurable)
- Send IPC message to renderer to toggle listening

#### [MODIFY] [Overlay.tsx](file:///home/robert/Coding/equalizer/frontend/src/Overlay.tsx)
- Add `isListening` state
- When paused: disconnect processor, show "⏸️ PAUSED" status
- When resumed: reconnect audio pipeline

---

## P3: Position Persistence

### Goal
Remember where user dragged the overlay; restore on next launch.

### Implementation

#### [MODIFY] [Overlay.tsx](file:///home/robert/Coding/equalizer/frontend/src/Overlay.tsx)
```typescript
// On window move, save position to localStorage
useEffect(() => {
  const saved = localStorage.getItem('overlay-position');
  if (saved) setPosition(JSON.parse(saved));
}, []);

// On drag end, persist
window.addEventListener('moved', () => {
  localStorage.setItem('overlay-position', JSON.stringify({x, y}));
});
```

---

## P4: Custom Coach Personalities

### Goal
Allow users to switch between coaching styles:
- **Aggressive**: "Demand 20% more. Now."
- **Diplomatic**: "Consider exploring their budget constraints."
- **Socratic**: "What would happen if you asked why?"

### Implementation

#### [NEW] [backend/services/personalities.py](file:///home/robert/Coding/equalizer/backend/services/personalities.py)
```python
PERSONALITIES = {
    "tactical": "You are a Tactical Commander...",
    "diplomatic": "You are a Diplomatic Advisor...",
    "socratic": "You are a Socratic Mentor..."
}
```

#### [MODIFY] [coach.py](file:///home/robert/Coding/equalizer/backend/services/coach.py)
- Accept `personality` parameter
- Load corresponding system prompt

#### [MODIFY] [Overlay.tsx](file:///home/robert/Coding/equalizer/frontend/src/Overlay.tsx)
- Add small dropdown or cycle button for personality selection

---

## P5: Speaker Diarization

> [!IMPORTANT]
> **Value**: Allows coach to distinguish between you and the other party, enabling more contextual advice like "They just said X, counter with Y."

### How Deepgram Diarization Works
- Enable `diarize=true` in the Deepgram request
- Transcripts return with `speaker: 0`, `speaker: 1` labels
- We can identify which speaker is the user (typically the one who speaks first)

### Implementation

#### [MODIFY] [audio_processor.py](file:///home/robert/Coding/equalizer/backend/services/audio_processor.py)
- Add `diarize=true` to Deepgram connection options
- Parse speaker labels from response
- Include speaker info in transcript callback

#### [MODIFY] [coach.py](file:///home/robert/Coding/equalizer/backend/services/coach.py)
- Update prompts to leverage speaker context
- "Speaker 0 (You)" vs "Speaker 1 (Counterparty)"
- Generate advice specifically about what the OTHER person said

---

## Verification Plan

| Feature | Test |
|---------|------|
| P1 System Audio | Play YouTube video, verify transcript appears |
| P2 Keyboard Toggle | Press hotkey, verify "⏸️ PAUSED" shows |
| P3 Position | Drag overlay, restart app, verify position restored |
| P4 Personalities | Switch to Diplomatic, verify softer tone in advice |
| P5 Diarization | Two people speak, verify speaker labels in logs |

---

## Recommended Order
1. ~~**P2 (Keyboard Toggle)**~~ ✅ Complete
2. ~~**P3 (Position Persistence)**~~ ✅ Complete
3. ~~**P4 (Personalities)**~~ ✅ Complete
4. **P5 (Speaker Diarization)** - Medium effort, high value, ~3-4 hours
5. **P1 (System Audio)** - Complex, requires testing, ~4+ hours

---

## User Review Required

> [!NOTE]
> **Which feature(s) would you like to tackle first?**
> I recommend starting with **P2 (Keyboard Toggle)** as a quick win.
