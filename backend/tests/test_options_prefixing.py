import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from core.analysis_engine.tactic_detection_v2 import TacticDetectorV2
from core.analysis_engine.schemas import TranscriptSegment

# Helper
def make_segment(text):
    return TranscriptSegment(text=text, speaker="User", timestamp=100.0)

def mock_openai_response(content_json):
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = json.dumps(content_json)
    return mock

@pytest.fixture
def detector():
    with patch("core.analysis_engine.tactic_detection_v2.AsyncOpenAI") as mock_ai:
        det = TacticDetectorV2(api_key="fake")
        det.client.chat.completions.create = AsyncMock()
        yield det

@pytest.mark.asyncio
async def test_options_coerced_prefixes(detector):
    # Mock return with bad prefixes
    # "Ask for rationale" -> "Consider ask for rationale" or similar
    # "Request a breakdown" -> "Consider request a breakdown"
    # "Do not accept." -> "Consider do not accept" (although this is weird English, the prefixer is a simple prepender if regex doesn't catch it, or frontend handles it too. But logic says "Auto-fix prefix... valid_options.append(f"Consider {opt[0].lower() + opt[1:]}")")
    
    bad_options = ["Ask for rationale.", "Request a breakdown.", "Do not accept."]
    
    detector.client.chat.completions.create.return_value = mock_openai_response({
        "signals": [{
            "category": "ANCHORING",
            "subtype": "numeric_anchor",
            "confidence": 0.8,
            "options": bad_options,
            "message": "Anchor."
        }]
    })

    new_segs = [make_segment("High price.")]
    signals = await detector.detect_tactics([], new_segments=new_segs)
    
    assert len(signals) == 1
    opts = signals[0].options
    assert len(opts) == 3
    
    # Verify coercion
    # "Ask for rationale." -> "Consider ask for rationale."
    assert opts[0] == "Consider ask for rationale."
    assert opts[1] == "Consider request a breakdown."
    assert opts[2] == "Consider do not accept."
    
    # Check that they start with allowed prefixes
    allowed = ["One option is to", "Consider", "Another approach could be", "You might"]
    for o in opts:
        assert any(o.startswith(p) for p in allowed)

@pytest.mark.asyncio
async def test_valid_prefixes_preserved(detector):
    good_options = [
        "One option is to ask why.",
        "Consider waiting.",
        "Another approach could be silence."
    ]
    
    detector.client.chat.completions.create.return_value = mock_openai_response({
        "signals": [{
            "category": "ANCHORING",
            "subtype": "numeric_anchor", 
            "confidence": 0.8,
            "options": good_options,
            "message": "Anchor."
        }]
    })
    
    signals = await detector.detect_tactics([], new_segments=[make_segment("...")])
    opts = signals[0].options
    
    assert opts[0] == "One option is to ask why."
    assert opts[1] == "Consider waiting."
    assert opts[2] == "Another approach could be silence."
