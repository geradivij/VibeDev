"""
get_coding_context() — reads the most recently modified source file from
the filesystem and extracts language, symbols, git message, and time of day.
No external dependencies beyond the stdlib.
"""

import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

# Extensions → language name
_EXT_MAP = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".kt": "kotlin",
    ".swift": "swift",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".c": "c",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".scala": "scala",
    ".ex": "elixir",
    ".exs": "elixir",
    ".hs": "haskell",
    ".ml": "ocaml",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".sql": "sql",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".vue": "vue",
    ".svelte": "svelte",
}

# Directories to skip when scanning
_SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
    ".tox", "dist", "build", "target", ".next", ".nuxt", "coverage",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
}

_SOURCE_EXTS = set(_EXT_MAP.keys())


def _find_most_recent_file(watch_dir: Path, max_depth: int = 3) -> Path | None:
    """Return the most recently modified source file under watch_dir."""
    import time as _time
    best_path: Path | None = None
    best_mtime: float = 0.0
    deadline = _time.monotonic() + 5.0  # never scan for more than 5 seconds

    for root, dirs, files in os.walk(watch_dir):
        if _time.monotonic() > deadline:
            break
        # Prune skipped dirs in-place so os.walk doesn't descend into them
        dirs[:] = [
            d for d in dirs
            if d not in _SKIP_DIRS and not d.startswith(".")
        ]

        # Respect max_depth
        depth = len(Path(root).relative_to(watch_dir).parts)
        if depth >= max_depth:
            dirs.clear()

        for fname in files:
            if Path(fname).suffix.lower() not in _SOURCE_EXTS:
                continue
            fpath = Path(root) / fname
            try:
                mtime = fpath.stat().st_mtime
            except OSError:
                continue
            if mtime > best_mtime:
                best_mtime = mtime
                best_path = fpath

    return best_path


def _detect_language(path: Path) -> str:
    return _EXT_MAP.get(path.suffix.lower(), "unknown")


def _extract_symbols(path: Path, language: str) -> list[str]:
    """Extract top-level class and function names via lightweight regex."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    patterns: list[str] = []

    if language == "python":
        patterns = [
            r"^class\s+([A-Za-z_]\w*)",
            r"^def\s+([A-Za-z_]\w*)",
            r"^    def\s+([A-Za-z_]\w*)",
        ]
    elif language in ("typescript", "javascript"):
        patterns = [
            r"^(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_]\w*)",
            r"^(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_]\w*)",
            r"^(?:export\s+)?const\s+([A-Za-z_]\w*)\s*=\s*(?:async\s*)?\(",
        ]
    elif language == "rust":
        patterns = [
            r"^(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)",
            r"^(?:pub\s+)?struct\s+([A-Za-z_]\w*)",
            r"^(?:pub\s+)?enum\s+([A-Za-z_]\w*)",
            r"^(?:pub\s+)?trait\s+([A-Za-z_]\w*)",
        ]
    elif language == "go":
        patterns = [
            r"^func\s+(?:\([^)]+\)\s+)?([A-Za-z_]\w*)",
            r"^type\s+([A-Za-z_]\w*)\s+(?:struct|interface)",
        ]
    elif language in ("java", "kotlin", "scala", "csharp"):
        patterns = [
            r"(?:public|private|protected|internal)?\s+(?:static\s+)?(?:class|interface|enum|object)\s+([A-Za-z_]\w*)",
            r"(?:public|private|protected|internal)?\s+(?:static\s+)?(?:override\s+)?(?:suspend\s+)?(?:fun|void|def|async)\s+([A-Za-z_]\w*)\s*\(",
        ]

    symbols: list[str] = []
    for pat in patterns:
        for m in re.finditer(pat, source, re.MULTILINE):
            name = m.group(1)
            if not name.startswith("_") and name not in symbols:
                symbols.append(name)
            if len(symbols) >= 10:
                break
        if len(symbols) >= 10:
            break

    return symbols[:10]


def _get_git_message(path: Path) -> str | None:
    """Return the most recent git commit message for the file's repo."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-1", "--format=%s"],
            cwd=path.parent,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            msg = result.stdout.strip()
            return msg if msg else None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def get_coding_context(watch_dir: str | None = None) -> dict:
    """
    Find the most recently modified source file and return coding context.

    Returns a dict with keys:
        language, filename, symbols, git_message, hour_of_day, filepath
    """
    base = Path(watch_dir) if watch_dir else Path(
        os.environ.get("WATCH_DIR", "") or Path.home()
    )

    active_file = _find_most_recent_file(base)

    if active_file is None:
        return {
            "language": "unknown",
            "filename": None,
            "symbols": [],
            "git_message": None,
            "hour_of_day": datetime.now().hour,
            "filepath": None,
        }

    language = _detect_language(active_file)
    symbols = _extract_symbols(active_file, language)
    git_message = _get_git_message(active_file)

    return {
        "language": language,
        "filename": active_file.name,
        "symbols": symbols,
        "git_message": git_message,
        "hour_of_day": datetime.now().hour,
        "filepath": str(active_file),
    }
