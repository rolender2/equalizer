
Do not add additional directories unless explicitly required.

---

## 6. Backend Responsibilities (FastAPI)

### WebSocket Contract
- One WebSocket connection = one live session
- Receive **binary PCM audio**
- Send advice messages **only when warranted**

### Audio Processing
- Stream audio to Deepgram
- Buffer transcript until speech pauses
- Emit transcript only on pause (not word-by-word)

---

## 7. Coach Logic (Very Important)

The coach is a **tactical commander**, not a teacher.

### Decision Flow (Mandatory)
1. Ask: *Is advice warranted right now?* → YES / NO
2. Only if YES → generate advice

### Advice Rules (Hard Constraints)
- ≤ **7 words**
- Imperative voice
- No explanations
- No metadata
- No emojis
- If unsure or low confidence → **output NOTHING**

Returning verbose text is a defect.

---

## 8. Frontend Responsibilities (Electron + React)

### Overlay Window
- Always on top
- Frameless
- Transparent background
- Draggable
- Minimal footprint

### UI Rules
- Show **one advice card only**
- Auto-dismiss after **5–8 seconds**
- No history
- No scrolling
- No controls during calls

The UI must never distract the user.

---

## 9. Performance Targets

- Speech end → advice visible: **< 3 seconds**
- Advice frequency: **max one every ~10 seconds**
- Prefer missing advice over noisy advice

---

## 10. Testing Expectations (Lean)

### Required
- WebSocket connection lifecycle test
- Advice length enforcement test
- Advice cooldown test

### Optional
- WAV file → transcript → advice integration test

Do not build complex test harnesses.

---

## 11. Agent Decision Rules

When uncertain:
1. Choose the **simplest viable implementation**
2. Bias toward **less output**
3. Prefer **hardcoded defaults**
4. Ask only if blocked

---

## 12. Definition of “Done”

The MVP is complete when:
- Overlay floats above Zoom / Teams
- Speaking into the mic produces advice
- Advice appears quickly
- Advice is short and actionable
- The app does not distract the user

Anything beyond this is out of scope.

---

## Final Reminder

You are not building a platform.  
You are not building infrastructure.  
You are validating a **product moment**.

Ship accordingly.

