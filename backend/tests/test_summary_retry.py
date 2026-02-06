import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.analysis_engine.tactic_detection import TacticDetector


def mock_openai_response(content_raw):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content_raw
    return mock_response


@pytest.mark.asyncio
async def test_generate_summary_retries_on_invalid_json():
    with patch("core.analysis_engine.tactic_detection.AsyncOpenAI") as mock_ai:
        det = TacticDetector(api_key="fake")
        det.client.chat.completions.create = AsyncMock(side_effect=[
            mock_openai_response('{ "strong_move": "ok", '),  # invalid JSON
            mock_openai_response(json.dumps({
                "strong_move": "Held price line.",
                "missed_opportunity": "Did not ask for breakdown.",
                "improvement_tip": "Ask for line-item fees earlier."
            }))
        ])

        result = await det.generate_summary("Transcript", {"result": "won"}, expanded=False)
        assert result.strong_move == "Held price line."
        assert result.missed_opportunity == "Did not ask for breakdown."
        assert result.improvement_tip == "Ask for line-item fees earlier."
