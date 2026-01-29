import pytest
import asyncio
from unittest.mock import MagicMock, patch
import sys

# Mocking core modules to avoid OpenAI connection during tests
sys.modules["core.analysis_engine.tactic_detection"] = MagicMock()
sys.modules["core.analysis_engine.tactic_detection_v2"] = MagicMock()

from services.coach import Coach
from core.analysis_engine.schemas import TranscriptSegment

@pytest.fixture
def coach():
    # Patch the detectors in Coach class to avoid instantiation
    with patch("services.coach.TacticDetector"), \
         patch("services.coach.TacticDetectorV2"):
        # user_speaker_id default is 0
        c = Coach(mode="live", negotiation_type="General", user_speaker_id=0)
        return c

def test_speaker_id_extraction(coach):
    # Test int pass-through
    assert coach._speaker_id_from_segment(0) == 0
    assert coach._speaker_id_from_segment(1) == 1
    
    # Test "Speaker N" string parsing
    assert coach._speaker_id_from_segment("Speaker 0") == 0
    assert coach._speaker_id_from_segment("Speaker 1") == 1
    assert coach._speaker_id_from_segment("speaker 5") == 5
    
    # Test explicit strings (legacy safety)
    assert coach._speaker_id_from_segment("USER") == -2
    assert coach._speaker_id_from_segment("COUNTERPARTY") == -2
    
    # Test garbage/unknown
    assert coach._speaker_id_from_segment("Unknown") == -1
    assert coach._speaker_id_from_segment(None) == -1

def test_role_labeling_user_is_0(coach):
    coach.set_user_speaker_id(0)
    
    # Int inputs
    assert coach._role_label(0) == "USER"
    assert coach._role_label(1) == "COUNTERPARTY"
    
    # String inputs
    assert coach._role_label("Speaker 0") == "USER"
    assert coach._role_label("Speaker 1") == "COUNTERPARTY"

def test_role_labeling_user_is_1(coach):
    coach.set_user_speaker_id(1)
    
    # Int inputs
    assert coach._role_label(1) == "USER"
    assert coach._role_label(0) == "COUNTERPARTY"
    
    # String inputs
    assert coach._role_label("Speaker 1") == "USER"
    assert coach._role_label("Speaker 0") == "COUNTERPARTY"

def test_legacy_compatibility(coach):
    # If "USER" or "COUNTERPARTY" is passed, it should be preserved
    assert coach._role_label("USER") == "USER"
    assert coach._role_label("COUNTERPARTY") == "COUNTERPARTY"

def test_process_transcript_buffer(coach):
    async def run_test():
        # Clear buffer
        coach.audio_buffer = []
        
        # Add User line (id 0)
        await coach.process_transcript("Hello world", 0)
        assert coach.audio_buffer[-1].speaker == "USER"
        
        # Add Counterparty line (id 1)
        await coach.process_transcript("Hi there", 1)
        assert coach.audio_buffer[-1].speaker == "COUNTERPARTY"
        
        # Add "Speaker 0" string
        await coach.process_transcript("I am user", "Speaker 0")
        assert coach.audio_buffer[-1].speaker == "USER"

        # Add "Speaker 1" string
        await coach.process_transcript("I am counterparty", "Speaker 1")
        assert coach.audio_buffer[-1].speaker == "COUNTERPARTY"

    asyncio.run(run_test())

