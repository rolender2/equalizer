import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from core.analysis_engine.tactic_detection_v2 import TacticDetectorV2
from core.analysis_engine.schemas import TranscriptSegment


def make_segment(text, speaker="COUNTERPARTY", timestamp=100.0):
    return TranscriptSegment(text=text, speaker=speaker, timestamp=timestamp)


def mock_openai_response(content_json):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(content_json)
    return mock_response


@pytest.fixture
def detector():
    with patch("core.analysis_engine.tactic_detection_v2.AsyncOpenAI") as mock_ai:
        det = TacticDetectorV2(api_key="fake")
        det.client.chat.completions.create = AsyncMock()
        yield det


@pytest.mark.asyncio
async def test_new_tactics_passthrough(detector):
    detector.client.chat.completions.create.return_value = mock_openai_response({
        "signals": [{
            "category": "COMMITMENT_TRAP",
            "subtype": "conditional_commitment",
            "confidence": 0.9,
            "headline": "Conditional Commitment",
            "why": "They are requesting a commitment in exchange for a concession.",
            "best_question": "If we agree, what changes on your side?",
            "options": ["Consider clarifying the condition."],
            "evidence": "If I do X, will you do Y?",
            "message": "Commitment asked."
        }]
    })

    signals = await detector.detect_tactics([], new_segments=[make_segment("If I do X, will you do Y?")])
    assert len(signals) == 1
    assert signals[0].category == "COMMITMENT_TRAP"
    assert signals[0].subtype == "conditional_commitment"


@pytest.mark.asyncio
async def test_ad_filter_skips_analysis():
    with patch("core.analysis_engine.tactic_detection_v2.AsyncOpenAI") as mock_ai:
        det = TacticDetectorV2(api_key="fake")
        det.client.chat.completions.create = AsyncMock()

        signals = await det.detect_tactics([], new_segments=[make_segment("This episode is brought to you by Acme.")])
        assert signals == []
        assert not det.client.chat.completions.create.called


@pytest.mark.asyncio
async def test_framing_threshold_filters_low_confidence(detector):
    detector.client.chat.completions.create.return_value = mock_openai_response({
        "signals": [{
            "category": "FRAMING",
            "subtype": "minimization",
            "confidence": 0.8,
            "headline": "Minimization",
            "why": "Downplaying impact.",
            "best_question": "What does that include?",
            "options": ["Consider probing for details."],
            "evidence": "It's just a small fee.",
            "message": "Minimization."
        }]
    })

    signals = await detector.detect_tactics([], new_segments=[make_segment("It's just a small fee.")])
    assert signals == []
