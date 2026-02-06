import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.responses import JSONResponse

from main import generate_session_summary


def mock_openai_response(content_json):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(content_json)
    return mock_response


@pytest.mark.asyncio
async def test_summary_with_null_outcome():
    project_root = Path(__file__).resolve().parent.parent.parent
    sessions_dir = project_root / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_id = "test_summary_null_outcome"
    session_path = sessions_dir / f"{session_id}.json"

    session_payload = {
        "session_id": session_id,
        "negotiation_type": "Vendor",
        "outcome": None,
        "transcripts": [
            {"speaker": "COUNTERPARTY", "text": "Here is the offer.", "timestamp": "now"}
        ],
    }
    session_path.write_text(json.dumps(session_payload, indent=2))

    try:
        with patch("core.analysis_engine.tactic_detection.AsyncOpenAI") as mock_ai:
            det = mock_ai.return_value
            det.chat.completions.create = AsyncMock(return_value=mock_openai_response({
                "strong_move": "Held firm.",
                "missed_opportunity": "Did not ask for breakdown.",
                "improvement_tip": "Ask for line-item fees earlier."
            }))

            result = await generate_session_summary(session_id)
            assert not isinstance(result, JSONResponse)
            assert result.get("strong_move") == "Held firm."
            assert result.get("missed_opportunity") == "Did not ask for breakdown."
            assert result.get("improvement_tip") == "Ask for line-item fees earlier."

            saved = json.loads(session_path.read_text())
            assert "reflection" in saved
            details = saved.get("summary_details")
            assert details is not None
            assert details.get("total_transcripts") == 1
            assert details.get("total_advice") == 0
    finally:
        if session_path.exists():
            session_path.unlink()
