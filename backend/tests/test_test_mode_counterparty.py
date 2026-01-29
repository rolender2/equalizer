import pytest
import asyncio
from unittest.mock import MagicMock, patch
import sys

# Mocking core modules to avoid OpenAI connection during tests
sys.modules["core.analysis_engine.tactic_detection"] = MagicMock()
sys.modules["core.analysis_engine.tactic_detection_v2"] = MagicMock()

from services.coach import Coach

@pytest.fixture
def coach():
    # Patch the detectors in Coach class to avoid instantiation
    with patch("services.coach.TacticDetector"), \
         patch("services.coach.TacticDetectorV2"):
        # user_speaker_id default is 0
        c = Coach(mode="live", negotiation_type="General", user_speaker_id=0)
        return c

def test_test_mode_logic(coach):
    # 1. Default (Off)
    assert coach.test_mode_counterparty is False
    assert coach._role_label(0) == "USER"
    assert coach._role_label(1) == "COUNTERPARTY"
    
    # 2. Enable Test Mode
    coach.set_test_mode_counterparty(True)
    assert coach.test_mode_counterparty is True
    
    # 3. Verify Mapping Unchanged (test mode only affects gating, not labels)
    assert coach._role_label(0) == "USER"
    assert coach._role_label(1) == "COUNTERPARTY"
    assert coach._role_label("Speaker 0") == "USER"
    
    # 4. Disable Test Mode
    coach.set_test_mode_counterparty(False)
    assert coach.test_mode_counterparty is False
    assert coach._role_label(0) == "USER"
