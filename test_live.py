"""
End-to-end smoke test:
  1. get_coding_context
  2. search_tracks (yt-dlp → YouTube Music)
  3. play_track (opens browser)
  4. get_now_playing (check state)
"""
import asyncio
import json
import time
from dotenv import load_dotenv
load_dotenv(".env")

from vibe.context import get_coding_context
from vibe.music import search_tracks
from vibe.player import play_track, get_now_playing


async def main():
    print("=== 1. get_coding_context ===")
    ctx = get_coding_context(watch_dir=".")
    print(json.dumps(ctx, indent=2))

    fake_vibe = {
        "energy": 0.75,
        "valence": 0.6,
        "focus": "deep",
        "primary_language": "punjabi",
        "lastfm_tags": ["punjabi trap", "desi beats"],
        "spotify_query": "punjabi trap beats coding",
        "fallback_query": "lo-fi hip hop focus beats",
        "label": "late-night grind",
    }

    print("\n=== 2. search_tracks (YouTube Music via yt-dlp) ===")
    result = await search_tracks(fake_vibe)
    print(f"Query: {result['query']}")
    print(f"Validated tags: {result['validated_tags']}")
    print(f"Found {len(result['tracks'])} tracks:")
    for i, t in enumerate(result["tracks"]):
        mins, secs = divmod(t["duration_seconds"], 60)
        line = f"  [{i}] {t['title']} — {t['uploader']} ({mins}:{secs:02d})"
        print(line.encode("ascii", errors="replace").decode("ascii"))

    if not result["tracks"]:
        print("No tracks found — check yt-dlp install")
        return

    print("\n=== 3. play_track (opens browser) ===")
    track = result["tracks"][0]
    played = play_track(track)
    print(json.dumps(played, indent=2))

    print("\n=== 4. get_now_playing (after 2s) ===")
    time.sleep(2)
    now = get_now_playing()
    print(json.dumps(now, indent=2))
    print(f"\nNext track should play in ~{now.get('seconds_remaining', '?') - 30}s")


asyncio.run(main())
