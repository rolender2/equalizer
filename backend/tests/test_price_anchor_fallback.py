import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from core.analysis_engine.tactic_detection import TacticDetector
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
    with patch("core.analysis_engine.tactic_detection.AsyncOpenAI") as mock_ai:
        det = TacticDetector(api_key="fake")
        det.client.chat.completions.create = AsyncMock()
        yield det


@pytest.mark.asyncio
async def test_anchor_fallback_dollar_amount(detector):
    detector.client.chat.completions.create.return_value = mock_openai_response({
        "signals": [{"category": "NONE", "subtype": "none", "confidence": 0.0, "options": [], "message": "None"}]
    })

    segments = [make_segment("The price is $50,000.")]
    signals = await detector.detect_tactics(segments)

    assert signals[0].category == "ANCHORING"
    assert signals[0].subtype == "numeric_anchor"
    assert signals[0].confidence >= 0.8


@pytest.mark.asyncio
async def test_anchor_fallback_k_suffix(detector):
    detector.client.chat.completions.create.return_value = mock_openai_response({
        "signals": [{"category": "NONE", "subtype": "none", "confidence": 0.0, "options": [], "message": "None"}]
    })

    segments = [make_segment("The price is 50k.")]
    signals = await detector.detect_tactics(segments)

    assert signals[0].category == "ANCHORING"
    assert signals[0].subtype == "numeric_anchor"


@pytest.mark.asyncio
async def test_no_fallback_for_non_negotiation_payment(detector):
    detector.client.chat.completions.create.return_value = mock_openai_response({
        "signals": [{"category": "NONE", "subtype": "none", "confidence": 0.0, "options": [], "message": "None"}]
    })

    segments = [make_segment("Last year I paid $50,000 for a car.")]
    signals = await detector.detect_tactics(segments)

    assert signals == []
