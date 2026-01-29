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
async def test_v2_numeric_anchor_override_on_none():
    detector = None
    with patch("core.analysis_engine.tactic_detection_v2.AsyncOpenAI") as mock_ai:
        det = TacticDetectorV2(api_key="fake")
        det.client.chat.completions.create = AsyncMock(return_value=mock_openai_response({
            "signals": [{"category": "NONE", "subtype": "none", "confidence": 1.0, "evidence": "The price is $50,000."}]
        }))

        new_segs = [make_segment("The price is $50,000.")]
        signals = await det.detect_tactics([], new_segments=new_segs)

        assert len(signals) == 1
        assert signals[0].category == "ANCHORING"
        assert signals[0].subtype == "numeric_anchor"
        assert signals[0].confidence >= 0.8


@pytest.mark.asyncio
async def test_v2_numeric_anchor_override_exclusion():
    with patch("core.analysis_engine.tactic_detection_v2.AsyncOpenAI") as mock_ai:
        det = TacticDetectorV2(api_key="fake")
        det.client.chat.completions.create = AsyncMock(return_value=mock_openai_response({
            "signals": [{"category": "NONE", "subtype": "none", "confidence": 1.0, "evidence": "Last year I paid $50,000 for a car."}]
        }))

        new_segs = [make_segment("Last year I paid $50,000 for a car.")]
    signals = await det.detect_tactics([], new_segments=new_segs)

    # Accept NONE (no override) or empty; must not force numeric_anchor
    if signals:
        assert signals[0].category == "NONE"
