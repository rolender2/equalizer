from pathlib import Path
import json
import logging

# Setup mocking for SessionRecorder since we want to test its logic
# We will just import it directly but patch the sessions dir path logic implicitly 
# by creating a dummy file where it expects it.
# Wait, better to just unit test the function, but it relies on file I/O.
# Let's create a test session file first.

from services.session_recorder import SessionRecorder

def test_swap():
    # 1. Create dummy session
    sid = "test_swap_session"
    # Logic in SessionRecorder is: project_root = Path(__file__).resolve().parent.parent.parent
    # So if it's in backend/services/session_recorder.py, root is equalizer/
    # And sessions is equalizer/sessions
    
    # We are in backend/verify_swap.py. Parent is equalizer/
    project_root = Path(__file__).resolve().parent.parent
    sessions_dir = project_root / "sessions"
    sessions_dir.mkdir(exist_ok=True)
    
    file_path = sessions_dir / f"{sid}.json"
    
    data = {
        "session_id": sid,
        "transcripts": [
            {"speaker": "user", "text": "I say this"},
            {"speaker": "counterparty", "text": "They say that"}
        ]
    }
    
    with open(file_path, 'w') as f:
        json.dump(data, f)
        
    print(f"Created test session: {file_path}")
    
    # 2. Swap index 0 (User -> Counterparty)
    print("Swapping index 0 (expect user -> counterparty)...")
    success = SessionRecorder.swap_speaker_role(sid, 0)
    if not success:
        print("FAILED: swap_speaker_role returned False")
        return
        
    with open(file_path, 'r') as f:
        new_data = json.load(f)
    
    s0 = new_data["transcripts"][0]["speaker"]
    print(f"Index 0 speaker: {s0}")
    if s0 != "counterparty":
        print("FAILED: Expected counterparty")
        return

    # 3. Swap index 0 again (Counterparty -> User)
    print("Swapping index 0 again (expect counterparty -> user)...")
    SessionRecorder.swap_speaker_role(sid, 0)
    
    with open(file_path, 'r') as f:
        new_data = json.load(f)
        
    s0_2 = new_data["transcripts"][0]["speaker"]
    print(f"Index 0 speaker: {s0_2}")
    if s0_2 != "user":
        print("FAILED: Expected user")
        return

    print("✅ SUCCESS: Swapping works correctly")

if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    test_swap()
