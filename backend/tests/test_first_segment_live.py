import pytest
from unittest.mock import AsyncMock, patch

from services.coach import Coach
from core.analysis_engine.schemas import TacticSignal


def create_signal(cat, sub="numeric_anchor", conf=0.9):
    return TacticSignal(
        category=cat,
        subtype=sub,
        confidence=conf,
        evidence="The price is $50,000.",
        timestamp=100.0,
        options=[],
        message="Anchor detected."
    )


@pytest.mark.asyncio
async def test_live_first_segment_triggers_in_test_mode():
    with patch("services.coach.TacticDetector"), \
         patch("services.coach.TacticDetectorV2") as mock_v2_cls:
        mock_v2_inst = mock_v2_cls.return_value
        mock_v2_inst.detect_tactics = AsyncMock(return_value=[create_signal("ANCHORING")])

        coach = Coach(mode="live", negotiation_type="Vendor", user_speaker_id=0)
        coach.detector_v2 = mock_v2_inst

        coach.set_test_mode_counterparty(True)
        result = await coach.process_transcript("The price is $50,000.", 0)

        assert coach.audio_buffer[-1].speaker == "COUNTERPARTY"
        assert result is not None
        assert result["category"] == "ANCHORING"
        assert mock_v2_inst.detect_tactics.called


@pytest.mark.asyncio
async def test_live_first_segment_gated_for_user():
    with patch("services.coach.TacticDetector"), \
         patch("services.coach.TacticDetectorV2") as mock_v2_cls:
        mock_v2_inst = mock_v2_cls.return_value
        mock_v2_inst.detect_tactics = AsyncMock(return_value=[create_signal("ANCHORING")])

        coach = Coach(mode="live", negotiation_type="Vendor", user_speaker_id=0)
        coach.detector_v2 = mock_v2_inst

        coach.set_test_mode_counterparty(False)
        result = await coach.process_transcript("The price is $50,000.", 0)

        assert coach.audio_buffer[-1].speaker == "USER"
        assert result is None
        assert not mock_v2_inst.detect_tactics.called
