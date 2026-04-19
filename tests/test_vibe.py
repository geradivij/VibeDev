"""Tests for vibe/infer.py — mocks MCP sampling, no network calls."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from vibe.infer import _build_user_message, _parse_vibe_json, infer_vibe, _FALLBACK_VIBE


# ---------------------------------------------------------------------------
# _build_user_message
# ---------------------------------------------------------------------------

def test_build_user_message_full():
    ctx = {
        "language": "python",
        "filename": "train.py",
        "symbols": ["ModelTrainer", "fit"],
        "git_message": "fix: loss converging",
        "hour_of_day": 23,
    }
    msg = _build_user_message(ctx)
    assert "python" in msg
    assert "train.py" in msg
    assert "ModelTrainer" in msg
    assert "fix: loss converging" in msg
    assert "23" in msg

def test_build_user_message_missing_optional():
    ctx = {"language": "go", "filename": None, "symbols": [], "git_message": None, "hour_of_day": 9}
    msg = _build_user_message(ctx)
    assert "go" in msg
    assert "none detected" in msg
    assert "no recent commit" in msg


# ---------------------------------------------------------------------------
# _parse_vibe_json
# ---------------------------------------------------------------------------

VALID_VIBE = {
    "energy": 0.8,
    "valence": 0.6,
    "focus": "deep",
    "primary_language": "punjabi",
    "lastfm_tags": ["punjabi trap", "desi beats"],
    "spotify_query": "punjabi trap coding playlist",
    "fallback_query": "dark lo-fi hip hop focus",
    "label": "late-night ML grind",
}

def test_parse_valid_json():
    import json
    result = _parse_vibe_json(json.dumps(VALID_VIBE))
    assert result["energy"] == 0.8
    assert result["focus"] == "deep"
    assert result["label"] == "late-night ML grind"

def test_parse_clamps_energy():
    import json
    bad = VALID_VIBE.copy()
    bad["energy"] = 1.5
    bad["valence"] = -0.2
    result = _parse_vibe_json(json.dumps(bad))
    assert result["energy"] == 1.0
    assert result["valence"] == 0.0

def test_parse_strips_markdown_fences():
    import json
    wrapped = f"```json\n{json.dumps(VALID_VIBE)}\n```"
    result = _parse_vibe_json(wrapped)
    assert result["energy"] == 0.8

def test_parse_fallback_on_garbage():
    result = _parse_vibe_json("not json at all!!!")
    assert result == _FALLBACK_VIBE

def test_parse_embedded_json():
    import json
    text = f"Here is the vibe: {json.dumps(VALID_VIBE)} done."
    result = _parse_vibe_json(text)
    assert result["label"] == "late-night ML grind"


# ---------------------------------------------------------------------------
# infer_vibe (async, mocked ctx)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_infer_vibe_calls_sample():
    import json

    mock_result = MagicMock()
    mock_result.text = json.dumps(VALID_VIBE)

    mock_ctx = MagicMock()
    mock_ctx.sample = AsyncMock(return_value=mock_result)

    context = {
        "language": "python",
        "filename": "server.py",
        "symbols": ["main"],
        "git_message": "feat: add vibe tool",
        "hour_of_day": 14,
    }

    result = await infer_vibe(context, mock_ctx)
    mock_ctx.sample.assert_called_once()
    assert result["label"] == "late-night ML grind"

@pytest.mark.asyncio
async def test_infer_vibe_fallback_on_sample_failure():
    mock_ctx = MagicMock()
    mock_ctx.sample = AsyncMock(side_effect=RuntimeError("host unavailable"))

    result = await infer_vibe({}, mock_ctx)
    assert result == _FALLBACK_VIBE
