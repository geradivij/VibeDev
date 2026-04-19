"""
search_tracks(query, fallback_query) — YouTube search via yt-dlp.

Claude picks the query based on coding context. No vibe dict, no sampling.
"""

import asyncio
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import yt_dlp


def _log(msg: str) -> None:
    print(f"[music] {msg}", file=sys.stderr, flush=True)

_LASTFM_BASE = "https://ws.audioscrobbler.com/2.0/"
_SEARCH_RESULTS = 10
_MIN_DURATION = 60
_MAX_DURATION = 8 * 60

_executor = ThreadPoolExecutor(max_workers=2)
_YTDLP_TIMEOUT = 20


class _QuietLogger:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


def _search_sync(query: str, max_results: int = _SEARCH_RESULTS) -> list[dict]:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "logger": _QuietLogger(),
        "extract_flat": True,
        "skip_download": True,
    }
    _log(f"_search_sync: query={query!r}")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            entries = info.get("entries", []) if info else []
        _log(f"_search_sync: got {len(entries)} entries before duration filter")
        tracks = []
        for entry in entries:
            if not entry:
                continue
            duration = entry.get("duration") or 0
            if not (_MIN_DURATION <= duration <= _MAX_DURATION):
                _log(f"  filtered out: {entry.get('title','?')} duration={duration}")
                continue
            video_id = entry.get("id")
            if not video_id:
                continue
            tracks.append({
                "title": entry.get("title", "Unknown"),
                "uploader": entry.get("uploader") or entry.get("channel", ""),
                "duration_seconds": int(duration),
                "url": f"https://music.youtube.com/watch?v={video_id}",
            })
        _log(f"_search_sync: returning {len(tracks)} tracks")
        return tracks
    except Exception:
        _log(f"_search_sync: EXCEPTION:\n{traceback.format_exc()}")
        return []


async def _search_async(query: str) -> list[dict]:
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(_executor, _search_sync, query),
            timeout=_YTDLP_TIMEOUT,
        )
    except asyncio.TimeoutError:
        return []


async def search_tracks(query: str, fallback_query: str = "lo-fi hip hop focus") -> dict:
    """
    Search YouTube for tracks matching query.

    Args:
        query: Search string — Claude picks this based on coding context.
               E.g. "AP Dhillon", "Karan Aujla", "Drake dark", "Travis Scott"
        fallback_query: Used if primary returns no results.

    Returns:
        tracks: list of {title, uploader, duration_seconds, url}
        query: which query was used
        used_fallback: bool
    """
    tracks = await _search_async(query)
    used_fallback = False

    if not tracks:
        tracks = await _search_async(fallback_query)
        used_fallback = True

    return {
        "tracks": tracks,
        "query": fallback_query if used_fallback else query,
        "used_fallback": used_fallback,
    }
