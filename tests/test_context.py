"""Tests for vibe/context.py — no external dependencies."""

import os
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from vibe.context import (
    _detect_language,
    _extract_symbols,
    _find_most_recent_file,
    get_coding_context,
)


# ---------------------------------------------------------------------------
# _detect_language
# ---------------------------------------------------------------------------

def test_detect_python():
    assert _detect_language(Path("train.py")) == "python"

def test_detect_typescript():
    assert _detect_language(Path("app.tsx")) == "typescript"

def test_detect_unknown():
    assert _detect_language(Path("binary.exe")) == "unknown"

def test_detect_case_insensitive():
    assert _detect_language(Path("Train.PY")) == "python"


# ---------------------------------------------------------------------------
# _extract_symbols
# ---------------------------------------------------------------------------

PYTHON_SRC = textwrap.dedent("""\
    class ModelTrainer:
        def __init__(self):
            pass

        def fit(self, X, y):
            pass

        def backward_pass(self):
            pass

    def train_loop():
        pass
""")

def test_extract_python_symbols(tmp_path):
    f = tmp_path / "train.py"
    f.write_text(PYTHON_SRC)
    symbols = _extract_symbols(f, "python")
    assert "ModelTrainer" in symbols
    assert "fit" in symbols
    assert "backward_pass" in symbols
    assert "train_loop" in symbols

TS_SRC = textwrap.dedent("""\
    export class UserService {
      constructor() {}
    }

    export async function fetchUser(id: string) {
      return null;
    }

    export const createUser = async (data: any) => {
      return null;
    };
""")

def test_extract_typescript_symbols(tmp_path):
    f = tmp_path / "service.ts"
    f.write_text(TS_SRC)
    symbols = _extract_symbols(f, "typescript")
    assert "UserService" in symbols
    assert "fetchUser" in symbols
    assert "createUser" in symbols

def test_extract_empty_file(tmp_path):
    f = tmp_path / "empty.py"
    f.write_text("")
    assert _extract_symbols(f, "python") == []

def test_extract_nonexistent_file():
    assert _extract_symbols(Path("/nonexistent/file.py"), "python") == []


# ---------------------------------------------------------------------------
# _find_most_recent_file
# ---------------------------------------------------------------------------

def test_find_most_recent_file(tmp_path):
    older = tmp_path / "older.py"
    newer = tmp_path / "newer.py"
    older.write_text("# old")
    newer.write_text("# new")

    # Ensure newer has a later mtime
    import time
    time.sleep(0.01)
    newer.touch()

    result = _find_most_recent_file(tmp_path)
    assert result == newer

def test_find_skips_node_modules(tmp_path):
    node_mod = tmp_path / "node_modules"
    node_mod.mkdir()
    (node_mod / "index.js").write_text("// skip me")
    real = tmp_path / "app.py"
    real.write_text("# keep me")

    result = _find_most_recent_file(tmp_path)
    assert result == real

def test_find_empty_dir(tmp_path):
    result = _find_most_recent_file(tmp_path)
    assert result is None


# ---------------------------------------------------------------------------
# get_coding_context (integration)
# ---------------------------------------------------------------------------

def test_get_coding_context_with_python_file(tmp_path):
    f = tmp_path / "model.py"
    f.write_text(PYTHON_SRC)

    ctx = get_coding_context(watch_dir=str(tmp_path))
    assert ctx["language"] == "python"
    assert ctx["filename"] == "model.py"
    assert isinstance(ctx["symbols"], list)
    assert isinstance(ctx["hour_of_day"], int)
    assert 0 <= ctx["hour_of_day"] <= 23

def test_get_coding_context_empty_dir(tmp_path):
    ctx = get_coding_context(watch_dir=str(tmp_path))
    assert ctx["language"] == "unknown"
    assert ctx["filename"] is None
    assert ctx["symbols"] == []
