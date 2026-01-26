import pytest
import time
import json
from unittest.mock import AsyncMock, MagicMock, patch
from services.coach import Coach
from core.analysis_engine.schemas import TranscriptSegment, TacticSignal

# Helper signal creators
def create_signal(cat, sub="none", conf=0.9, opts=None):
    if opts is None: opts = ["Consider verifying."]
    return TacticSignal(
        category=cat,
        subtype=sub,
        confidence=conf,
        evidence="text",
        timestamp=100.0,
        options=opts,
        message="msg"
    )

@pytest.fixture
def coach():
    # Patch detectors
    with patch("services.coach.TacticDetector"), \
         patch("services.coach.TacticDetectorV2") as mock_v2_cls:
        
        # Setup V2 instance mock
        mock_v2_inst = mock_v2_cls.return_value
        mock_v2_inst.detect_tactics = AsyncMock(return_value=[])
        
        c = Coach(mode="live", negotiation_type="General", user_speaker_id=0)
        c.detector_v2 = mock_v2_inst
        c.window_size_seconds = 0.0 # Force analysis
        yield c

@pytest.mark.asyncio
async def test_last_line_new_isolation(coach):
    # Arrange: Add multiple lines
    # We need to simulate that process_transcript appends to buffer
    # And then calls _analyze_window
    
    coach.detector_v2.detect_tactics.return_value = []
    
    await coach.process_transcript("Context 1", "Speaker 1")
    await coach.process_transcript("Context 2", "Speaker 1")
    await coach.process_transcript("Target Line", "Speaker 1")
    
    # Assert calls to detector
    # Should have called detect_tactics 3 times (due to window_size=0).
    # The LAST call should have:
    # segments = [Context 1, Context 2, Target Line] (or slice)
    # new_segments = [Target Line] (ONLY the last one)
    
    assert coach.detector_v2.detect_tactics.call_count == 3
    
    # Get last call args
    call_args = coach.detector_v2.detect_tactics.call_args
    kwargs = call_args.kwargs
    
    new_segs = kwargs["new_segments"]
    assert len(new_segs) == 1
    assert new_segs[0].text == "Target Line"
    
    # Context should contain previous ones (depending on slice limit logic in coach)
    # Coach: context_segments = self.audio_buffer[-12:]
    # So context should have all 3
    ctx_segs = kwargs["segments"]
    assert len(ctx_segs) >= 3
    assert ctx_segs[-1].text == "Target Line" # context includes everything as per buffer

@pytest.mark.asyncio
async def test_role_gating_behavior(coach):
    # Set User Speaker ID = 0 (default)
    # Speaker 0 -> USER. Speaker 1 -> COUNTERPARTY.
    
    # Case 1: USER speaks live line
    # Mock detector to find nothing (or verify we don't send if we did, but prompts silence it)
    # Actually, verify mapping first.
    
    await coach.process_transcript("I am user", "Speaker 0")
    # Buffer should show "USER"
    assert coach.audio_buffer[-1].speaker == "USER"
    
    await coach.process_transcript("I am counterparty", "Speaker 1")
    assert coach.audio_buffer[-1].speaker == "COUNTERPARTY"
    
    # Verify that if last line is USER, we typically get NONE (via Prompt rules).
    # But since we are mocking detector, let's verify that IF detector follows prompt (returns NONE)
    # Coach suppresses it.
    
    coach.detector_v2.detect_tactics.return_value = [create_signal("NONE", "none", 1.0)]
    result = await coach.process_transcript("User line", "Speaker 0")
    assert result is None # Silent because NONE logic in Coach
    
    # Case 2: COUNTERPARTY speaks live line -> Valid Signal
    coach.detector_v2.detect_tactics.return_value = [create_signal("URGENCY", "deadline", 0.9)]
    result = await coach.process_transcript("Valid today only.", "Speaker 1")
    
    assert result is not None
    data = json.loads(result)
    assert data["content"]["category"] == "URGENCY"

@pytest.mark.asyncio
async def test_dedupe_cooldown(coach):
    # Arrange: Valid signal
    coach.detector_v2.detect_tactics.return_value = [create_signal("URGENCY", "deadline", 0.9)]
    
    # First emit: Success
    res1 = await coach.process_transcript("Line 1", "Speaker 1")
    assert res1 is not None
    
    # Second emit (Same type, immediate): Suppressed
    res2 = await coach.process_transcript("Line 2", "Speaker 1")
    assert res2 is None
    
    # Third emit (Different type): Success
    coach.detector_v2.detect_tactics.return_value = [create_signal("AUTHORITY", "policy", 0.9)]
    res3 = await coach.process_transcript("Line 3", "Speaker 1")
    assert res3 is not None
    
    # Fourth emit (Same original type, after 46 sec): Success
    coach.detector_v2.detect_tactics.return_value = [create_signal("URGENCY", "deadline", 0.9)]
    
    with patch("time.time", side_effect=[1000, 1050, 1060]): # Mock time progress? 
        # Hard to patch time inside the method call flow easily without patching module level
        # We can just manually set coach properties to simulate time passing if the logic uses time.time()
        # Coach uses time.time() inside.
        pass

    # Alternative Dedupe Test with manual state manipulation
    coach._last_emit_key = ("URGENCY", "deadline")
    coach._last_emit_ts = time.time() - 10 # Only 10s passed
    
    # Emit same
    coach.detector_v2.detect_tactics.return_value = [create_signal("URGENCY", "deadline", 0.9)]
    res4 = await coach.process_transcript("Line 4", "Speaker 1")
    assert res4 is None # Suppressed
    
    # Expire timer
    coach._last_emit_ts = time.time() - 50 # 50s passed
    res5 = await coach.process_transcript("Line 5", "Speaker 1")
    assert res5 is not None
