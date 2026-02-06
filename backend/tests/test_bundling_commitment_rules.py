import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.analysis_engine.schemas import TranscriptSegment
from core.analysis_engine.tactic_detection_v2 import TacticDetectorV2


def mock_openai_response(content_json):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(content_json)
    return mock_response


@pytest.mark.asyncio
async def test_bundling_override_when_llm_none():
    det = TacticDetectorV2(api_key="fake")
    det.client.chat.completions.create = AsyncMock(return_value=mock_openai_response({
        "signals": [
            {"category": "NONE", "subtype": "none", "confidence": 0.1, "evidence": "", "options": [], "message": "No signal"}
        ]
    }))

    seg = TranscriptSegment(speaker="COUNTERPARTY", text="We include a protection plan and doc fee in the package.", timestamp=1.0)
    signals = await det.detect_tactics(segments=[seg], new_segments=[seg])
    assert signals
    assert signals[0].category == "BUNDLING"
    assert signals[0].subtype == "add_on_bundle"


@pytest.mark.asyncio
async def test_commitment_trap_requires_conditional_exchange():
    det = TacticDetectorV2(api_key="fake")
    det.client.chat.completions.create = AsyncMock(return_value=mock_openai_response({
        "signals": [
            {
                "category": "COMMITMENT_TRAP",
                "subtype": "conditional_commitment",
                "confidence": 0.9,
                "headline": "Commitment Check",
                "why": "n/a",
                "best_question": "n/a",
                "evidence": "We should get paid for the work.",
                "options": ["Consider asking for a fair rate."],
                "message": "Commitment asked."
            }
        ]
    }))

    seg = TranscriptSegment(speaker="COUNTERPARTY", text="We should get paid for the work.", timestamp=1.0)
    signals = await det.detect_tactics(segments=[seg], new_segments=[seg])
    assert signals
    assert signals[0].category == "NONE"


@pytest.mark.asyncio
async def test_social_proof_ignores_shopping_advice():
    det = TacticDetectorV2(api_key="fake")
    det.client.chat.completions.create = AsyncMock(return_value=mock_openai_response({
        "signals": [
            {
                "category": "SOCIAL_PROOF",
                "subtype": "herd_reference",
                "confidence": 0.9,
                "headline": "Social proof",
                "why": "n/a",
                "best_question": "n/a",
                "evidence": "You should talk to multiple design firms before deciding.",
                "options": ["Consider comparing quotes."],
                "message": "Social proof"
            }
        ]
    }))

    seg = TranscriptSegment(speaker="COUNTERPARTY", text="You should talk to multiple design firms before deciding.", timestamp=1.0)
    signals = await det.detect_tactics(segments=[seg], new_segments=[seg])
    assert signals
    assert signals[0].category == "NONE"
