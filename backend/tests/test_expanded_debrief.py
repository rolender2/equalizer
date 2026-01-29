import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from core.analysis_engine.tactic_detection import TacticDetector


def mock_openai_response(content_json):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(content_json)
    return mock_response


@pytest.mark.asyncio
async def test_generate_summary_expanded():
    with patch("core.analysis_engine.tactic_detection.AsyncOpenAI") as mock_ai:
        det = TacticDetector(api_key="fake")
        det.client.chat.completions.create = AsyncMock(return_value=mock_openai_response({
            "strong_move": "Held price line.",
            "missed_opportunity": "Did not ask for breakdown.",
            "improvement_tip": "Ask for line-item fees earlier.",
            "expanded_insights": [
                "Anchor set early by counterparty.",
                "Policy shield used on doc fee."
            ]
        }))

        result = await det.generate_summary("Transcript", {"result": "won"}, expanded=True)
        assert result.expanded_insights is not None
        assert len(result.expanded_insights) == 2
