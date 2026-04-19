"""
Queue-based player with background auto-advance.

queue_tracks(tracks)  — load track list, start playing, auto-advance
skip_track()          — skip to next
get_now_playing()     — current track + queue position + time remaining
"""

import asyncio
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from vibe import webplayer

_executor = ThreadPoolExecutor(max_workers=2)


def _log(msg: str) -> None:
    print(f"[player] {msg}", file=sys.stderr, flush=True)

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

_queue: list[dict] = []
_queue_index: int = 0
_started_at: Optional[float] = None
_advance_task: Optional[asyncio.Task] = None

_ADVANCE_BEFORE_END = 10   # open next tab this many seconds before song ends


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _play_index(index: int) -> dict:
    global _queue_index, _started_at
    if not _queue or index >= len(_queue):
        return {"success": False, "error": "No track at that index"}
    track = _queue[index]
    _queue_index = index
    _started_at = time.time()
    webplayer.update(track["url"], track.get("title", ""), track.get("uploader", ""))
    return {
        "success": True,
        "title": track.get("title"),
        "uploader": track.get("uploader"),
        "duration_seconds": int(track.get("duration_seconds") or 0),
        "url": track["url"],
        "queue_index": index,
        "queue_total": len(_queue),
    }


async def _refresh_queue() -> bool:
    """Re-run context detection, pick new artists, search, reload queue."""
    try:
        from vibe.context import get_coding_context as _get_ctx, _pick_artists
        from vibe.music import _search_async

        loop = asyncio.get_event_loop()
        _log("refreshing queue: getting coding context")
        ctx = await asyncio.wait_for(
            loop.run_in_executor(_executor, _get_ctx),
            timeout=8.0,
        )
        artists = _pick_artists(ctx)
        _log(f"refreshing queue: picked artists {artists}")

        tracks = []
        for artist in artists:
            results = await _search_async(artist)
            tracks.extend(results[:4])

        if not tracks:
            _log("refreshing queue: no tracks found, keeping current queue")
            return False

        import random
        random.shuffle(tracks)

        global _queue, _queue_index, _started_at
        _queue = tracks
        _queue_index = 0
        _started_at = None
        _log(f"refreshing queue: loaded {len(tracks)} new tracks")
        _play_index(0)
        return True
    except Exception as e:
        _log(f"refreshing queue: error {e!r}")
        return False


async def _advance_loop():
    """Advance to next track before current song ends. Refreshes queue when done."""
    while True:
        await asyncio.sleep(3)
        if _started_at is None or not _queue:
            continue
        track = _queue[_queue_index]
        duration = int(track.get("duration_seconds") or 0)
        if duration == 0:
            continue
        remaining = duration - (time.time() - _started_at)
        if remaining <= _ADVANCE_BEFORE_END:
            next_index = _queue_index + 1
            if next_index < len(_queue):
                _play_index(next_index)
            else:
                # Queue exhausted — do a fresh vibe check and reload
                _log("queue ended, doing vibe check refresh")
                await _refresh_queue()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def queue_tracks(tracks: list[dict]) -> dict:
    """
    Load tracks and start playing. Background loop auto-advances before
    each song ends, opening a new browser tab for each track.
    """
    global _queue, _queue_index, _started_at, _advance_task

    if not tracks:
        return {"success": False, "error": "Empty track list"}

    _queue = tracks
    _queue_index = 0
    _started_at = None

    if _advance_task and not _advance_task.done():
        _advance_task.cancel()
    _advance_task = asyncio.create_task(_advance_loop())

    webplayer.start()   # open controller tab (idempotent)
    result = _play_index(0)
    result["message"] = (
        f"Playing 1 of {len(tracks)}. Auto-advancing through queue."
    )
    return result


def skip_track() -> dict:
    """Skip to the next track in the queue."""
    if not _queue:
        return {"success": False, "error": "No queue loaded"}
    return _play_index((_queue_index + 1) % len(_queue))


def get_now_playing() -> dict:
    """Current track + elapsed/remaining time + queue position."""
    if _started_at is None or not _queue:
        return {"is_playing": False, "title": None, "queue_total": 0}
    track = _queue[_queue_index]
    duration = int(track.get("duration_seconds") or 0)
    elapsed = time.time() - _started_at
    remaining = max(0.0, duration - elapsed) if duration else None
    return {
        "is_playing": True,
        "title": track.get("title"),
        "uploader": track.get("uploader"),
        "duration_seconds": duration,
        "elapsed_seconds": round(elapsed),
        "seconds_remaining": round(remaining) if remaining is not None else None,
        "url": track.get("url"),
        "queue_index": _queue_index,
        "queue_total": len(_queue),
    }
