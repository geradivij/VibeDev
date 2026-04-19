"""
VibeDev MCP Server

Flow:
  1. get_coding_context()
  2. search_tracks(query, fallback_query)   ← Claude picks the query
  3. queue_tracks(tracks)                  ← server auto-advances from here

Extra: skip_track(), get_now_playing()
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from dotenv import load_dotenv
from fastmcp import FastMCP, Context

load_dotenv(Path(__file__).parent / ".env")

from vibe.context import get_coding_context as _get_coding_context
from vibe.music import search_tracks as _search_tracks
from vibe.player import (
    queue_tracks as _queue_tracks,
    skip_track as _skip_track,
    get_now_playing as _get_now_playing,
)

_thread_pool = ThreadPoolExecutor(max_workers=4)

mcp = FastMCP(
    "VibeDev",
    instructions="""
VibeDev plays mood-matched music from the Indian subcontinent while the user codes.
Always start with get_coding_context(), then follow the next_action field in the result exactly.
""",
)


@mcp.tool()
async def get_coding_context(watch_dir: str = "") -> dict:
    """
    Read the most recently modified source file.
    Returns: language, filename, symbols, hour_of_day, active_project.
    """
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(_thread_pool, _get_coding_context, watch_dir or None),
            timeout=8.0,
        )
    except asyncio.TimeoutError:
        from datetime import datetime
        return {
            "language": "unknown", "filename": None, "symbols": [],
            "hour_of_day": datetime.now().hour, "filepath": None,
        }


@mcp.tool()
async def search_tracks(query: str, fallback_query: str = "lo-fi hip hop focus") -> dict:
    """
    Search YouTube for tracks matching query (via yt-dlp). 2-8 min tracks only.

    Args:
        query: Artist or song to search — e.g. "AP Dhillon", "Karan Aujla", "Drake Nonstop"
        fallback_query: Used if primary returns nothing.

    Returns: tracks [{title, uploader, duration_seconds, url}], query, used_fallback.
    Pass the tracks list directly to queue_tracks().
    """
    return await _search_tracks(query, fallback_query)


@mcp.tool()
async def queue_tracks(tracks: list) -> dict:
    """
    Load tracks and start playing. Auto-advances to next track before each song ends.
    Opens a new browser tab per track — no further action needed from you.

    Args:
        tracks: The tracks list from search_tracks()["tracks"]
    """
    return await _queue_tracks(tracks)


@mcp.tool()
def skip_track() -> dict:
    """Skip to the next track in the queue."""
    return _skip_track()


@mcp.tool()
def get_now_playing() -> dict:
    """Current track, elapsed/remaining time, queue position."""
    return _get_now_playing()


if __name__ == "__main__":
    mcp.run()
