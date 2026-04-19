"""
Subprocess-based player using Edge/Chrome --app mode + dedicated profile.

--user-data-dir forces a completely independent browser process (can't attach
to an existing Edge/Chrome instance), giving us a real PID we can terminate.

First run: user logs into YouTube Music in the VibeDev window once.
Subsequent runs: profile is saved at ~/.vibedev/edge-profile, stays logged in.
"""

import os
import subprocess
import time
import webbrowser
from typing import Optional

_BROWSER_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
]

_PROFILE_DIR = os.path.join(os.path.expanduser("~"), ".vibedev", "edge-profile")
os.makedirs(_PROFILE_DIR, exist_ok=True)

_browser_path: Optional[str] = next(
    (p for p in _BROWSER_CANDIDATES if os.path.exists(p)), None
)
_proc: Optional[subprocess.Popen] = None


def _kill_current():
    global _proc
    if _proc is None:
        return
    try:
        _proc.terminate()
        _proc.wait(timeout=3)
    except Exception:
        try:
            _proc.kill()
        except Exception:
            pass
    _proc = None


def update(url: str, title: str, uploader: str):
    """Close the current track window and open the next one."""
    global _proc

    _kill_current()

    if not _browser_path:
        webbrowser.open(url)
        return

    # Small pause so the profile dir is fully released before reuse
    time.sleep(0.5)

    # Append autoplay param to the URL
    sep = "&" if "?" in url else "?"
    autoplay_url = f"{url}{sep}autoplay=1"

    _proc = subprocess.Popen([
        _browser_path,
        f"--app={autoplay_url}",
        f"--user-data-dir={_PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-features=TranslateUI",
        "--autoplay-policy=no-user-gesture-required",
    ])


def start():
    """No-op — first track opened via update(). Kept for API compatibility."""
    pass
