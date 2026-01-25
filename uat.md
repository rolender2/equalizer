# User Acceptance Test (UAT) - MVP Tightening (Phase 1-4)

This script verifies the **Negotiation Presets**, **Outcome Tagging**, **Signal Alerts**, and **Reflection Summary** features.
We will simulate four realistic negotiation scenarios to test different system configurations.

## Prerequisites
- [ ] Backend is running (`python main.py`) in `/backend`
- [ ] Frontend is running (`npm run electron:dev`) in `/frontend`
- [ ] Microphone is accessible

---

## Use Case 1: Salary Negotiation (New Job)
**Objective:** Verify "Salary" preset and "Won" outcome workflow.

### 1. Pre-Flight Setup
1. Launch the App.
2. **Verify:** You see the "NEGOTIATION PRE-FLIGHT" screen.
3. Select Scenario: **Salary**.
4. Click **INITIALIZE SYSTEMS**.
5. **Verify:** Overlay shows "🎤 LISTENING..." with green border.
6. **Verify:** Overlay displays "Scenario: Salary" in the status area.

### 2. Session Simulation
1. **Speak (User):** "I'm excited about the role, but I was hoping for a higher base salary."
2. **Simulate Counterparty (Play audio or speak):** "The best we can do is $120k."
    - **EXPECTATION:** AI says "ANCHOR DETECTED" or similar tactical advice.
3. **Wait for Advice:** Watch for a pop-up advice bubble.
   - *Note: Since we are in the MVP, the advice might just be text like "ANCHOR DETECTED" or similar tactical advice.*
4. **Speak (User):** "I understand. I'm looking for $135k based on market rates."

### 3. Conclusion & Tagging
1. Press `Ctrl+Shift+S` to **PAUSE** the session.
2. **Verify:** Status turns ORANGE ("PAUSED").
3. Click the red **"End Session & Save"** button.
4. **Verify:** The "Session Outcome" modal appears.
5. **Action:**
   - Result: **WON**
   - Confidence: **Slide to 5**
   - Notes: "Settled on $130k + Sign-on bonus."
6. Click **Save Outcome**.
7. **Verify:** Alert popup says "Outcome Saved Successfully!".

### 4. Data Verification
1. Go to project folder: `Coding/equalizer/sessions/`
2. Open the latest `.json` file.
3. **Verify:**
   - `negotiation_type`: "Salary"
   - `outcome.result`: "won"
   - `outcome.notes`: "Settled on $130k + Sign-on bonus."

---

## Use Case 2: Vendor Renewal (Tough)
**Objective:** Verify "Renewal" preset and "Lost" outcome workflow.

### 1. Pre-Flight Setup
1. Relaunch/Refresh the App (Status should be reset or click "Back" if available, or restart app).
2. **Verify:** "NEGOTIATION PRE-FLIGHT" screen.
3. Select Scenario: **Renewal**.
4. Click **INITIALIZE SYSTEMS**.

### 2. Session Simulation
1. **Speak (User):** "We need to discuss the 20% price increase on our contract."
64. **Simulate Counterparty:** "That is our standard inflation adjustment. It's non-negotiable."
    - **EXPECTATION:** AI should trigger a signal (e.g. "RIGIDITY DETECTED" or "ULTIMATUM").
3. **Speak (User):** "We cannot accept that. We might have to look at other vendors."

### 3. Conclusion & Tagging
1. Press `Ctrl+Shift+S` to **PAUSE**.
2. Click **"End Session & Save"**.
3. **Action:**
   - Result: **LOST**
   - Confidence: **Slide to 1**
   - Notes: "They stood firm. We need to RFP."
4. Click **Save Outcome**.

### 4. Data Verification
1. Open the latest `.json` file in `sessions/`.
2. **Verify:**
   - `negotiation_type`: "Renewal"
   - `outcome.result`: "lost"

---

## Use Case 3: Changing Coaches Mid-Flight
**Objective:** Verify changing Personality during a "General" session.

### 1. Pre-Flight Setup
1. Select Scenario: **General**.
2. Click **INITIALIZE SYSTEMS**.

### 2. Session Simulation
1. **Verify Default:** Current Coach icon says "⚔️ Tactical".
2. **Action:** Click the Coach button (or wait 5s and click it).
3. **Verify:** Coach changes to "🤝 Diplomatic".
4. **Speak (User):** "I think we can find a middle ground."
5. **Verify Backend Log:** Check terminal for `Coach personality changed to: diplomatic`.
    - **EXPECTATION:** Backend logs confirm: `Coach personality changed to: diplomatic`.

### 3. Quick Save
1. Pause -> End -> Save (Result: Deferred).
2. Verify JSON shows `negotiation_type`: "General".

---

## Use Case 4: Reflection Summary (Phase 4)
**Objective:** Verify the AI-generated post-session reflection.

### 1. Pre-Flight Setup
1. Select Scenario: **Salary** (or any).
2. Click **INITIALIZE SYSTEMS**.
3. Click **Skip** (Mic Only).

### 2. Session Simulation
1. **Speak (User):** "I'd like to discuss my compensation."
2. **Simulate Counterparty:** "We're offering $100k."
3. **Wait for Advice:** AI should detect the anchor.
4. Click **End Session** button.

### 3. Outcome & Reflection
1. In the Outcome Modal:
   - Result: **WON**
   - Confidence: **4**
   - Notes: "Accepted $105k."
2. Click **Save Outcome**.
3. **Wait 3-5 seconds** for AI reflection to generate.
4. **Verify:** "Session Reflection" modal appears with:
   - ✅ **Strong Move**: What you did well
   - ⚠️ **Missed Opportunity**: What you could improve
   - 💡 **Tip for Next Time**: Actionable advice
5. Click **Done**.
6. **Verify:** App returns to Pre-Flight screen.

### 4. Data Verification
1. Open the latest `.json` file in `sessions/`.
2. **Verify:**
   - `reflection` object exists with `strong_move`, `missed_opportunity`, `improvement_tip`.

---

## Known Issues / What to Watch For
- **Window Dragging:** Can you drag the modals?
- **Alerts:** Do error alerts appear if you stop the backend mid-session?
- **Audio:** Does the "Share Audio" vs "Skip" flow work as expected after Pre-flight?
- **Reflection Delay:** The AI takes 3-5 seconds to generate the summary.

