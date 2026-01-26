import pytest
import asyncio
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
    # Patch the AsyncOpenAI client initialization or just the client inside
    with patch("core.analysis_engine.tactic_detection_v2.AsyncOpenAI") as mock_ai:
        det = TacticDetectorV2(api_key="fake")
        # Ensure client.chat.completions.create is an AsyncMock
        det.client.chat.completions.create = AsyncMock()
        yield det

@pytest.mark.asyncio
async def test_detect_anchoring_numeric(detector):
    # Setup Mock
    detector.client.chat.completions.create.return_value = mock_openai_response({
        "signals": [{
            "category": "ANCHORING",
            "subtype": "numeric_anchor",
            "confidence": 0.9,
            "evidence": "The price is $50,000.",
            "options": ["One option is to counter.", "Consider asking for breakdown."],
            "message": "Anchor detected."
        }]
    })

    new_segs = [make_segment("The price is $50,000.")]
    signals = await detector.detect_tactics([], new_segments=new_segs)

    assert len(signals) == 1
    assert signals[0].category == "ANCHORING"
    assert signals[0].subtype == "numeric_anchor"
    assert len(signals[0].options) == 2

@pytest.mark.asyncio
async def test_detect_urgency_deadline(detector):
    detector.client.chat.completions.create.return_value = mock_openai_response({
        "signals": [{
            "category": "URGENCY",
            "subtype": "deadline",
            "confidence": 0.85,
            "evidence": "Only valid today.",
            "options": ["One option is to pause.", "Consider verifying."],
            "message": "Deadline detected."
        }]
    })

    new_segs = [make_segment("This offer is only valid today.")]
    signals = await detector.detect_tactics([], new_segments=new_segs)

    assert signals[0].category == "URGENCY"
    assert signals[0].subtype == "deadline"

@pytest.mark.asyncio
async def test_detect_authority_manager(detector):
    detector.client.chat.completions.create.return_value = mock_openai_response({
        "signals": [{
            "category": "AUTHORITY",
            "subtype": "manager_deferral",
            "confidence": 0.9,
            "evidence": "Check with manager.",
            "options": ["One option is to ask who decides."],
            "message": "Authority constraint."
        }]
    })

    new_segs = [make_segment("I need to check with my manager.")]
    signals = await detector.detect_tactics([], new_segments=new_segs)

    assert signals[0].category == "AUTHORITY"
    assert signals[0].subtype == "manager_deferral"

@pytest.mark.asyncio
async def test_context_priority_regression(detector):
    # Context has URGENCY, New has AUTHORITY
    # The detector logic itself doesn't "decide" this, the prompt does. 
    # But strictly speaking, our test should verify that if the LLM follows instructions, we interpret it right.
    # Since we MOCK the LLM, we are verifying that we pass the right data TO the LLM and parse the result.
    # To truly test the prompt logic, we'd need a real LLM call (integration test).
    # But per instructions, this is a unit test. We will assume the prompt works as designed (verified in smoke/live).
    # We just ensure we process a correct response correctly.
    
    # Let's verify we send the right text to the LLM at least?
    # Or simulate that "New" signals are returned.
    
    detector.client.chat.completions.create.return_value = mock_openai_response({
        "signals": [{
            "category": "AUTHORITY", 
            "subtype": "manager_deferral",
            "confidence": 0.9,
            "message": "Manager check.",
            "options": ["Consider asking timeframe."]
        }]
    })
    
    context = [make_segment("This expires today.", speaker="Counterparty")]
    new_segs = [make_segment("I need to check with my manager.", speaker="Counterparty")]
    
    signals = await detector.detect_tactics(context, new_segments=new_segs)
    
    assert signals[0].category == "AUTHORITY"
    
    # Optionally verify call arguments separated context/new
    call_args = detector.client.chat.completions.create.call_args
    sent_messages = call_args.kwargs['messages']
    user_content = sent_messages[1]['content']
    assert "PASSED CONTEXT" in user_content
    assert "This expires today" in user_content
    assert "NEW SECTIONS" in user_content
    assert "check with my manager" in user_content

@pytest.mark.asyncio
async def test_options_prefix_enforcement(detector):
    # Mock return with bad prefixes
    detector.client.chat.completions.create.return_value = mock_openai_response({
        "signals": [{
            "category": "ANCHORING",
            "subtype": "numeric_anchor",
            "confidence": 0.9,
            "options": ["Ask for a discount.", "Tell them no.", "Consider walking away."],
            "message": "Low anchor."
        }]
    })

    new_segs = [make_segment("Price is high.")]
    signals = await detector.detect_tactics([], new_segments=new_segs)
    
    opts = signals[0].options
    # "Ask for a discount." -> Should become "Consider ask for a discount." or similar
    # "Tell them no." -> "Consider tell them no."
    # "Consider walking away." -> Kept as is.
    
    assert opts[2] == "Consider walking away."
    assert opts[0].startswith("Consider") or opts[0].startswith("One option") or opts[0].startswith("Another approach") or opts[0].startswith("You might")
    assert opts[1].startswith("Consider") or opts[0].startswith("One option") or opts[0].startswith("Another approach") or opts[0].startswith("You might")

@pytest.mark.asyncio
async def test_seller_ish_filtering_removal(detector):
    # 1. Test removal of banned phrases
    detector.client.chat.completions.create.return_value = mock_openai_response({
        "signals": [{
            "category": "URGENCY",
            "subtype": "deadline",
            "confidence": 0.9,
            "options": [
                "Consider asking for more time.", 
                "One option is to emphasize the benefits of acting quickly.", # BANNED
                "Another approach could be to create urgency." # BANNED
            ],
            "message": "Deadline."
        }]
    })

    new_segs = [make_segment("Hurry up.")]
    signals = await detector.detect_tactics([], new_segments=new_segs)
    
    opts = signals[0].options
    assert len(opts) == 1
    assert "Consider asking for more time." in opts[0]
    
@pytest.mark.asyncio
async def test_seller_ish_filtering_retry(detector):
    # 2. Test Retry if all options filtered
    
    # First response: All banned
    bad_response = {
        "signals": [{
            "category": "URGENCY",
            "subtype": "deadline",
            "confidence": 0.9,
            "options": ["Highlight urgency to close.", "Push them to sign."],
            "message": "Bad advice."
        }]
    }
    
    # Second response (Retry): Good options
    good_response = {
        "signals": [{
            "category": "URGENCY",
            "subtype": "deadline",
            "confidence": 0.9,
            "options": ["Consider requesting an extension.", "One option is to verify the deadline."],
            "message": "Good advice."
        }]
    }
    
    detector.client.chat.completions.create.side_effect = [
        mock_openai_response(bad_response),
        mock_openai_response(good_response)
    ]
    
    new_segs = [make_segment("Hurry up.")]
    signals = await detector.detect_tactics([], new_segments=new_segs)
    
    assert len(signals) == 1
    opts = signals[0].options
    assert len(opts) == 2
    assert "Consider requesting an extension." in opts
    
    # Verify retry prompt suffix was added in second call
    assert detector.client.chat.completions.create.call_count == 2
    call_args_2 = detector.client.chat.completions.create.call_args_list[1]
    system_msg = call_args_2.kwargs['messages'][0]['content']
    assert "IMPORTANT: Options must be user-protective" in system_msg

@pytest.mark.asyncio
async def test_json_robustness_malformed(detector):
    # First call malformed, second call valid
    detector.client.chat.completions.create.side_effect = [
        mock_openai_raw_response("This is not JSON."),
        mock_openai_response({
            "signals": [{
                "category": "NONE",
                "subtype": "none",
                "confidence": 0.0,
                "options": [],
                "message": "Nothing."
            }]
        })
    ]
    
    new_segs = [make_segment("Hello.")]
    signals = await detector.detect_tactics([], new_segments=new_segs)
    
    assert len(signals) == 1
    assert signals[0].category == "NONE"
    
    # Verify retry happened
    assert detector.client.chat.completions.create.call_count == 2
