import pytest
from unittest.mock import AsyncMock, patch

from services.coach import Coach
from core.analysis_engine.schemas import TacticSignal


def create_signal(cat, sub="none", conf=0.9):
    return TacticSignal(
        category=cat,
        subtype=sub,
        confidence=conf,
        evidence="text",
        timestamp=100.0,
        options=["Consider verifying."],
        message="msg"
    )


@pytest.mark.asyncio
async def test_test_mode_overrides_role_and_allows_analysis():
    with patch("services.coach.TacticDetector"), \
         patch("services.coach.TacticDetectorV2") as mock_v2_cls:
        mock_v2_inst = mock_v2_cls.return_value
        mock_v2_inst.detect_tactics = AsyncMock(return_value=[create_signal("URGENCY", "deadline", 0.9)])

        coach = Coach(mode="live", negotiation_type="Vendor", user_speaker_id=0)
        coach.detector_v2 = mock_v2_inst
        coach.window_size_seconds = 0.0

        # Test mode ON: speaker_id=0 should be treated as COUNTERPARTY
        coach.set_test_mode_counterparty(True)
        result = await coach.process_transcript("This offer is only valid today.", 0)

        assert coach.audio_buffer[-1].speaker == "COUNTERPARTY"
        assert result is not None
        assert result["category"] == "URGENCY"
        assert mock_v2_inst.detect_tactics.called

        # Test mode OFF: speaker_id=0 should be USER and gated
        coach.set_test_mode_counterparty(False)
        mock_v2_inst.detect_tactics.reset_mock()
        result = await coach.process_transcript("This offer is only valid today.", 0)

        assert coach.audio_buffer[-1].speaker == "USER"
        assert result is None
        assert not mock_v2_inst.detect_tactics.called
