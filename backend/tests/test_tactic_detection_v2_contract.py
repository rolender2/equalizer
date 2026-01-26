import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from core.analysis_engine.tactic_detection_v2 import TacticDetectorV2
from core.analysis_engine.schemas import TranscriptSegment, TacticSignal

# Helper to create segments
def make_segment(text, speaker="User", timestamp=100.0):
    return TranscriptSegment(text=text, speaker=speaker, timestamp=timestamp)

# Helper to mock OpenAI response
def mock_openai_response(content_json):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(content_json)
    return mock_response

def mock_openai_raw_response(raw_text):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = raw_text
    return mock_response

@pytest.fixture
def detector():
    with patch("core.analysis_engine.tactic_detection_v2.AsyncOpenAI") as mock_ai:
        det = TacticDetectorV2(api_key="fake")
        det.client.chat.completions.create = AsyncMock()
        yield det

@pytest.mark.asyncio
async def test_options_never_contain_seller_closing_language(detector):
    # Mock return options containing banned phrases
    # Case insensitive check
    bad_options = [
        "One option is to emphasize the benefits of acting quickly to secure the deal.",
        "Highlight urgency to close.",
        "Consider asking for more time." # Good one
    ]
    
    detector.client.chat.completions.create.return_value = mock_openai_response({
        "signals": [{
            "category": "URGENCY",
            "subtype": "deadline",
            "confidence": 0.9,
            "options": bad_options,
            "message": "Urgency."
        }]
    })

    new_segs = [make_segment("Hurry up.")]
    signals = await detector.detect_tactics([], new_segments=new_segs)
    
    assert len(signals) == 1
    opts = signals[0].options
    assert len(opts) == 1
    assert "Consider asking for more time" in opts[0]
    # Ensure filtered ones are gone
    for opt in opts:
        assert "emphasize the benefits" not in opt.lower()
        assert "highlight urgency" not in opt.lower()
        assert "close" not in opt.lower()

@pytest.mark.asyncio
async def test_options_never_contain_seller_role_language(detector):
    # Mock return options with "your offering", "value proposition", etc.
    bad_options = [
        "Consider clarifying the value proposition of your service.",
        "One option is to justify your pricing.",
        "Another approach could be to pivot." # Good one
    ]
    
    detector.client.chat.completions.create.return_value = mock_openai_response({
        "signals": [{
            "category": "ANCHORING",
            "subtype": "numeric_anchor",
            "confidence": 0.8,
            "options": bad_options,
            "message": "Anchor."
        }]
    })
    
    new_segs = [make_segment("Price is high.")]
    signals = await detector.detect_tactics([], new_segments=new_segs)
    
    opts = signals[0].options
    assert len(opts) == 1
    # Check "pivot" is there
    # Note: "pivot" might be auto-prefixed if it doesn't match prefix list
    assert any("pivot" in o.lower() for o in opts)
    
    # Check bad ones are gone
    for opt in opts:
        assert "value proposition" not in opt.lower()
        assert "your pricing" not in opt.lower()

@pytest.mark.asyncio
async def test_tie_breaker_mixed_authority_urgency(detector):
    # Mock model output for NEW text -> Logic handles priority by user instruction? 
    # Actually, the PROMPT rules handle priority. Logic just parses what LLM says.
    # But if LLM says "URGENCY" with mixed cues, we accept it.
    # The requirement asks: "Mock model output... Return a signal with category URGENCY... Expect detector returns URGENCY."
    # So strictly this tests that we pass through the LLM's decision and normalize correctly.
    
    detector.client.chat.completions.create.return_value = mock_openai_response({
        "signals": [{
            "category": "URGENCY",
            "subtype": "deadline",
            "confidence": 0.9,
            "options": ["One option is to verify deadline."],
            "message": "Urgency first."
        }]
    })
    
    new_segs = [make_segment("That's company policy, and it's only available today.")]
    signals = await detector.detect_tactics([], new_segments=new_segs)
    
    assert signals[0].category == "URGENCY"
    assert signals[0].subtype == "deadline"

@pytest.mark.asyncio
async def test_new_only_isolation(detector):
    # Context: Urgency. New: Authority.
    # Mock output: Authority.
    detector.client.chat.completions.create.return_value = mock_openai_response({
        "signals": [{
            "category": "AUTHORITY",
            "subtype": "policy_shield",
            "confidence": 0.9,
            "options": ["Consider asking for exception."],
            "message": "Policy."
        }]
    })
    
    context = [make_segment("This offer is only valid today.")]
    new_segs = [make_segment("That's company policy.")]
    
    signals = await detector.detect_tactics(context, new_segments=new_segs)
    
    assert signals[0].category == "AUTHORITY"
    
    # Verify we sent appropriate prompt text (optional but good)
    call_args = detector.client.chat.completions.create.call_args
    user_content = call_args.kwargs['messages'][1]['content']
    assert "PASSED CONTEXT" in user_content
    assert "NEW SECTIONS" in user_content

@pytest.mark.asyncio
async def test_json_robustness_invalid_returns_empty(detector):
    # Mock invalid JSON twice (first call and retry call)
    detector.client.chat.completions.create.side_effect = [
        mock_openai_raw_response("Not JSON"),
        mock_openai_raw_response("Still not JSON")
    ]
    
    new_segs = [make_segment("Test.")]
    signals = await detector.detect_tactics([], new_segments=new_segs)
    
    assert signals == []
    # Should not raise

@pytest.mark.asyncio
async def test_json_repair_succeeds(detector):
    # First invalid, second (retry) valid
    detector.client.chat.completions.create.side_effect = [
        mock_openai_raw_response("Invalid"),
        mock_openai_response({
            "signals": [{
                "category": "NONE", 
                "confidence": 0,
                "options": [],
                "message": "None"
            }]
        })
    ]
    
    new_segs = [make_segment("Test.")]
    signals = await detector.detect_tactics([], new_segments=new_segs)
    assert len(signals) == 1
    assert signals[0].category == "NONE"
