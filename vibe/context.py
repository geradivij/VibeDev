"""
get_coding_context() — reads the most recently modified source file from
the filesystem and extracts language, symbols, git message, and time of day.
No external dependencies beyond the stdlib.
"""

import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path


def _log(msg: str) -> None:
    """Write diagnostic line to stderr so it appears in mcp-server-vibedev.log."""
    print(f"[context] {msg}", file=sys.stderr, flush=True)


# ── Artist picker ─────────────────────────────────────────────────────────────

_POOL: dict[str, list[str]] = {
    # Late night (after 10pm / before 10am) — ghazal, sufi, emotional
    "late_night": [
        # Ghazal legends
        "Jagjit Singh", "Ghulam Ali", "Mehdi Hassan", "Pankaj Udhas",
        "Talat Aziz", "Farida Khanum", "Anup Jalota", "Begum Akhtar",
        # Qawwali / sufi
        "Nusrat Fateh Ali Khan", "Abida Parveen", "Rahat Fateh Ali Khan",
        "Aziz Mian", "Pathanay Khan", "Sabri Brothers",
        # Late night emotional Bollywood
        "Arijit Singh", "KK", "Mohit Chauhan", "Javed Ali",
        "Mithoon", "Atif Aslam",
    ],

    # Intense (debugging, tests, Rust, Go) — desi rap underground
    "intense": [
        # Underground / desi rap
        "Seedhe Maut", "Prabh Deep", "Kr$na", "Emiway Bantai",
        "Karma", "Fotty Seven", "Pardhaan", "Dino James", "Deep Kalsi",
        "Slow Cheeta", "Hanumankind", "MC Stan", "Muhfaad", "Yunan",
        # Pakistani underground
        "Young Stunners", "Talha Anjum", "Talhah Yunus",
        # Hard Punjabi trap
        "DIVINE", "Raftaar", "Ikka", "Bohemia",
    ],

    # Deep grind (ML, long sessions, model/train/loss) — heavy Punjabi + sufi
    "deep_grind": [
        "Karan Aujla", "Sidhu Moosewala", "Shubh", "Bohemia", "Fazilpuria",
        "Jass Manak", "Jordan Sandhu", "Mickey Singh",
        # Coke Studio Pakistan for long flow
        "Coke Studio Pakistan", "Strings", "Junoon", "Ali Zafar",
        "Vital Signs", "Noori", "EP",
        # Sufi for grind
        "Nusrat Fateh Ali Khan", "Abida Parveen",
    ],

    # Energized (building, new feature, index/app/server) — party Bollywood + dance
    "energized": [
        "Diljit Dosanjh", "Badshah", "Yo Yo Honey Singh", "Jazzy B",
        "Nucleya", "Benny Dayal", "Sunidhi Chauhan", "Sukhwinder Singh",
        "Vishal Dadlani", "Sachin-Jigar", "Anirudh Ravichander",
        "Garry Sandhu", "B Praak", "Ritviz",
        # High energy film
        "Shankar Ehsaan Loy", "Salim-Sulaiman",
    ],

    # Focus / flow (general Python/JS/TS coding) — composers and instrumentals
    "focus": [
        # Bollywood composers (instrumental/score)
        "A.R. Rahman", "Amit Trivedi", "Ilaiyaraaja", "Vishal-Shekhar",
        "Pritam", "Shankar Ehsaan Loy", "Yuvan Shankar Raja",
        "Anirudh Ravichander", "Salim-Sulaiman", "Mithoon",
        "S. Thaman", "M.M. Keeravani", "Sohail Sen",
        # Classical instrumental
        "Ravi Shankar", "Zakir Hussain", "Hariprasad Chaurasia",
        "Shiv Kumar Sharma", "Ustad Amjad Ali Khan", "Sultan Khan",
        "L. Subramaniam", "U. Srinivas",
    ],

    # Chill (docs, markdown, yaml, morning) — indie, contemporary, light
    "chill": [
        # Indian indie
        "AP Dhillon", "Talwiinder", "Prateek Kuhad", "When Chai Met Toast",
        "The Local Train", "Anuv Jain", "Darshan Raval", "Hanita Bhambri",
        "Vishal Mishra", "Indian Ocean", "Lucky Ali", "Euphoria",
        "Silk Route", "Parikrama", "Easy Wanderlings",
        # Pakistani chill
        "Ali Sethi", "Arooj Aftab", "Hasan Raheem", "Meesha Shafi",
        # Old school mellow Bollywood
        "Kishore Kumar", "Mohammed Rafi", "Lata Mangeshkar",
        "Hemant Kumar", "Talat Mahmood",
    ],
}

_recent_artists: list[str] = []

_GENRES: dict[str, list[str]] = {
    "late_night": [
        "ghazal", "qawwali", "sufi", "sad bollywood", "pakistani classical",
        "acoustic indie", "coke studio", "semi-classical",
    ],
    "intense": [
        "desi hip hop", "underground rap", "punjabi trap", "indian hip hop",
        "pakistani hip hop", "drill", "hard bollywood", "indian electronic",
    ],
    "deep_grind": [
        "punjabi hip hop", "sufi rock", "coke studio", "dark bollywood",
        "pakistani rock", "cinematic instrumental", "qawwali fusion",
    ],
    "energized": [
        "punjabi pop", "bhangra", "bollywood dance", "desi party",
        "indian electronic", "tamil mass", "telugu mass", "filmi pop",
    ],
    "focus": [
        "indian film score", "bollywood instrumental", "hindustani instrumental",
        "carnatic fusion", "classical fusion", "lo-fi bollywood",
        "soft indie", "ambient desi",
    ],
    "chill": [
        "indian indie", "pakistani indie", "acoustic pop", "mellow bollywood",
        "desi r&b", "old bollywood", "folk fusion", "soft rock",
    ],
}

_EXTRA_POOL: dict[str, list[str]] = {
    "late_night": [
        "Hariharan", "Chitra Singh", "Iqbal Bano", "Runa Laila",
        "Wadali Brothers", "Fareed Ayaz", "Sanam Marvi", "Nooran Sisters",
        "Sonu Nigam", "Shaan", "Shreya Ghoshal", "Ali Sethi", "Arooj Aftab",
    ],
    "intense": [
        "Rawal", "Bharg", "Yashraj", "Raga", "Frappe Ash", "Ahmer",
        "Tsumyoki", "Sikander Kahlon", "Bella", "Gravity", "Faris Shafi",
        "Rap Demon", "JJ47", "Shareh", "Badshah", "Karan Aujla", "Shubh",
        "Sidhu Moosewala",
    ],
    "deep_grind": [
        "AP Dhillon", "Gurinder Gill", "Prem Dhillon", "Navaan Sandhu",
        "NseeB", "The PropheC", "Jaz Dhami", "Amrinder Gill", "Bayaan",
        "Kashmir", "Mekaal Hasan Band", "Rahat Fateh Ali Khan",
        "A.R. Rahman", "Amit Trivedi", "Vishal Bhardwaj",
    ],
    "energized": [
        "Devi Sri Prasad", "Thaman S", "Vijay Antony", "Yuvan Shankar Raja",
        "Daler Mehndi", "Sukhbir", "Mika Singh", "Hardy Sandhu",
        "Aastha Gill", "Neha Kakkar", "Kanika Kapoor", "Tanishk Bagchi",
        "Asees Kaur", "Amit Trivedi", "Vishal-Shekhar", "Pritam",
        "Ajay-Atul",
    ],
    "focus": [
        "Vishal Bhardwaj", "Ajay-Atul", "Sneha Khanwalkar", "Clinton Cerejo",
        "Ram Sampath", "Amaal Mallik", "Anupam Roy", "Santhosh Narayanan",
        "D. Imman", "Govind Vasantha", "Bismillah Khan", "Niladri Kumar",
        "Anoushka Shankar", "Rakesh Chaurasia", "Rahul Sharma",
        "Nitin Sawhney", "Karsh Kale",
    ],
    "chill": [
        "Lifafa", "Osho Jain", "Taba Chake", "Parekh & Singh", "Mali",
        "Samar Mehdi", "Dream Note", "The Yellow Diary", "Ankur Tewari",
        "Nikhil D'Souza", "Raghav Meattle", "Tejas", "Sanjeev Thomas",
        "Abdul Hannan", "Maanu", "Shamoon Ismail", "Sajjad Ali",
        "Asha Bhosle", "Mukesh", "Geeta Dutt",
    ],
}

for _category, _artists in _EXTRA_POOL.items():
    existing = _POOL.setdefault(_category, [])
    existing.extend(a for a in _artists if a not in existing)


def _pick_artist(context: dict) -> str:
    hour = context.get("hour_of_day", 12)
    language = context.get("language", "unknown")
    filename = (context.get("filename") or "").lower()
    symbols_str = " ".join(context.get("symbols") or []).lower()

    if hour < 10 or hour >= 22:
        category = "late_night"
    elif any(w in symbols_str for w in ["train", "model", "loss", "fit", "predict", "epoch"]):
        category = "deep_grind"
    elif any(w in filename for w in ["test", "spec"]) or "assert" in symbols_str:
        category = "intense"
    elif language in ("rust", "go"):
        category = "intense"
    elif any(w in filename for w in ["index", "app", "main", "server"]):
        category = "energized"
    elif language in ("markdown", "yaml", "toml") or "readme" in filename:
        category = "chill"
    elif language in ("python", "typescript", "javascript"):
        category = "focus"
    else:
        category = "chill"

    pool = _POOL[category]
    available = [a for a in pool if a not in _recent_artists[-3:]]
    if not available:
        available = pool

    artist = random.choice(available)
    _recent_artists.append(artist)
    if len(_recent_artists) > 8:
        _recent_artists.pop(0)

    _log(f"_pick_artist: category={category}, picked={artist!r}")
    return artist


def _category_for_context(context: dict) -> str:
    hour = context.get("hour_of_day", 12)
    language = context.get("language", "unknown")
    filename = (context.get("filename") or "").lower()
    symbols_str = " ".join(context.get("symbols") or []).lower()

    if hour < 10 or hour >= 22:
        return "late_night"
    if any(w in symbols_str for w in ["train", "model", "loss", "fit", "predict", "epoch"]):
        return "deep_grind"
    if any(w in filename for w in ["test", "spec"]) or "assert" in symbols_str:
        return "intense"
    if language in ("rust", "go"):
        return "intense"
    if any(w in filename for w in ["index", "app", "main", "server"]):
        return "energized"
    if language in ("markdown", "yaml", "toml") or "readme" in filename:
        return "chill"
    if language in ("python", "typescript", "javascript"):
        return "focus"
    return "chill"


def _pick_palette(context: dict, count: int = 12) -> dict:
    category = _category_for_context(context)
    pool = _POOL[category]
    available = [a for a in pool if a not in _recent_artists[-8:]]
    if not available:
        available = pool

    candidate_artists = random.sample(available, min(count, len(available)))
    _recent_artists.extend(candidate_artists[:4])
    del _recent_artists[:-16]

    genres = random.sample(_GENRES[category], min(4, len(_GENRES[category])))
    _log(
        f"_pick_palette: category={category}, genres={genres!r}, "
        f"artists={candidate_artists!r}"
    )
    return {
        "vibe_category": category,
        "genres": genres,
        "candidate_artists": candidate_artists,
        "suggested_query": candidate_artists[0],
        "avoid_recent_artists": _recent_artists[-8:],
    }


def _next_action(palette: dict) -> str:
    artists = ", ".join(repr(a) for a in palette["candidate_artists"])
    genres = ", ".join(repr(g) for g in palette["genres"])
    return (
        "Build a varied queue from the candidate artists and genres. "
        f"Candidate artists: [{artists}]. Genres: [{genres}]. "
        "Pick 4-6 different artists from candidate_artists. "
        "Call search_tracks separately for each selected artist, using "
        "fallback_query='AP Dhillon'. Combine 1-2 tracks per artist into one "
        "interleaved tracks list, then call queue_tracks with that mixed list. "
        "Do not search only one artist. Do not queue more than 2 tracks by the "
        "same artist."
    )

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
    deadline = _time.monotonic() + 2.0  # never scan for more than 2 seconds

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


def _appdata() -> Path:
    """Resolve %APPDATA% even when the env var is missing (Claude Desktop)."""
    val = os.environ.get("APPDATA")
    result = Path(val) if val else Path.home() / "AppData" / "Roaming"
    _log(f"_appdata() → {result} (APPDATA env={'set' if val else 'missing'})")
    return result


def _get_vscode_folder() -> Path | None:
    """Return the folder open in VS Code's last active window."""
    try:
        import json
        storage = _appdata() / "Code/User/globalStorage/storage.json"
        _log(f"_get_vscode_folder: checking {storage} exists={storage.exists()}")
        if not storage.exists():
            return None
        data = json.loads(storage.read_text(errors="replace"))
        folder_uri = data.get("windowsState", {}).get("lastActiveWindow", {}).get("folder", "")
        _log(f"_get_vscode_folder: folder_uri={folder_uri!r}")
        if not folder_uri:
            return None
        # Convert file:///c%3A/Users/... → C:/Users/...
        from urllib.parse import unquote
        path_str = unquote(folder_uri.replace("file:///", "")).replace("/", os.sep)
        # Fix drive letter: c: → C:
        if len(path_str) >= 2 and path_str[1] == ":":
            path_str = path_str[0].upper() + path_str[1:]
        p = Path(path_str)
        _log(f"_get_vscode_folder: resolved={p} exists={p.exists()}")
        return p if p.exists() else None
    except Exception as e:
        _log(f"_get_vscode_folder: exception {e!r}")
        return None


def _get_ps_history_dirs() -> list[Path]:
    """Return recently cd'd directories from PowerShell history."""
    try:
        history_file = (
            _appdata() / "Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt"
        )
        _log(f"_get_ps_history_dirs: checking {history_file} exists={history_file.exists()}")
        if not history_file.exists():
            return []
        lines = history_file.read_text(errors="replace").splitlines()
        dirs: list[Path] = []
        for line in reversed(lines[-200:]):
            line = line.strip()
            if line.lower().startswith("cd "):
                raw = line[3:].strip().strip('"').strip("'")
                p = Path(raw)
                if not p.is_absolute():
                    continue
                if p.exists() and p not in dirs:
                    dirs.append(p)
                if len(dirs) >= 3:
                    break
        _log(f"_get_ps_history_dirs: found {[str(d) for d in dirs]}")
        return dirs
    except Exception:
        return []



def get_coding_context(watch_dir: str | None = None) -> dict:
    """
    Find the most recently modified source file and return coding context.

    Sources checked (in priority order):
      1. VS Code lastActiveWindow folder
      2. Recent PowerShell cd directories
      3. WATCH_DIR env var / explicit watch_dir argument

    Returns a dict with keys:
        language, filename, symbols, git_message, hour_of_day, filepath,
        active_project (folder name), editor_sources (which sources detected)
    """
    # Build candidate directories to scan, most specific first.
    # Explicit watch_dir skips editor sources — used for testing and overrides.
    candidate_dirs: list[tuple[str, Path]] = []
    _log(f"get_coding_context: start, watch_dir={watch_dir!r}, WATCH_DIR={os.environ.get('WATCH_DIR')!r}")

    if watch_dir:
        candidate_dirs.append(("watch_dir", Path(watch_dir)))
    else:
        _log("get_coding_context: trying vscode source")
        vscode_folder = _get_vscode_folder()
        if vscode_folder:
            candidate_dirs.append(("vscode", vscode_folder))

        _log("get_coding_context: trying powershell source")
        for ps_dir in _get_ps_history_dirs():
            candidate_dirs.append(("powershell", ps_dir))

        env_dir = os.environ.get("WATCH_DIR", "")
        if env_dir:
            candidate_dirs.append(("watch_dir", Path(env_dir)))

        if not candidate_dirs:
            candidate_dirs.append(("home", Path.home()))

    _log(f"get_coding_context: candidates={[(s, str(d)) for s, d in candidate_dirs]}")

    # Try each source, use the first that finds a file
    active_file: Path | None = None
    source_used: str = "none"
    for source_name, directory in candidate_dirs:
        _log(f"get_coding_context: scanning {source_name}={directory}")
        f = _find_most_recent_file(directory, max_depth=3)
        _log(f"get_coding_context: {source_name} → {f}")
        if f is not None:
            active_file = f
            source_used = source_name
            break

    hour = datetime.now().hour
    _log(f"get_coding_context: active_file={active_file}, source={source_used}, hour={hour}")

    if active_file is None:
        partial = {
            "language": "unknown",
            "filename": None,
            "symbols": [],
            "hour_of_day": hour,
            "filepath": None,
            "active_project": None,
            "editor_sources": [s for s, _ in candidate_dirs],
        }
        artist = _pick_artist(partial)
        partial["suggested_query"] = artist
        partial["next_action"] = (
            f"Call search_tracks(query={artist!r}, fallback_query='AP Dhillon'). "
            f"Use this query exactly — do not substitute a different artist."
        )
        return partial

    language = _detect_language(active_file)
    symbols = _extract_symbols(active_file, language)

    result = {
        "language": language,
        "filename": active_file.name,
        "symbols": symbols,
        "hour_of_day": hour,
        "filepath": str(active_file),
        "active_project": active_file.parent.name,
        "editor_sources": [source_used],
    }
    artist = _pick_artist(result)
    result["suggested_query"] = artist
    result["next_action"] = (
        f"Call search_tracks(query={artist!r}, fallback_query='AP Dhillon'). "
        f"Use this query exactly — do not substitute a different artist."
    )
    return result
