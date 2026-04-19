# VibeDev MCP — Design Document
> Version 0.2 | Ambient music that matches what you're building

---

## What It Does

An MCP server that reads your active coding context and plays matching music. Claude reasons about the vibe and picks a search query. yt-dlp finds real tracks on YouTube. A local controller page manages playback in a single browser window.

**Music palette (desi-first):**
- Primary: Punjabi/Hindi artists — AP Dhillon, Shubh, Karan Aujla, Sidhu Moosewala, DIVINE, Diljit Dosanjh, Badshah, Arijit Singh
- Secondary: English hip-hop — Drake, Travis Scott, Kendrick Lamar, J Cole
- Fallback: English lo-fi/ambient

---

## Architecture (as built)

```
coding context → Claude picks query → yt-dlp finds tracks → controller page → YouTube Music window
```

### Tools (5)

| Tool | What it does |
|---|---|
| `get_coding_context()` | Scans WATCH_DIR for most recently modified source file. Returns language, filename, symbols, git message, hour. |
| `search_tracks(query, fallback_query)` | yt-dlp `ytsearch` → filters 1–8 min tracks → returns list of {title, uploader, duration_seconds, url} |
| `queue_tracks(tracks)` | Loads track list, starts webplayer controller, starts background advance loop |
| `skip_track()` | Advances to next track in queue |
| `get_now_playing()` | Returns current track + elapsed/remaining time + queue position |

### Vibe Inference

Original plan (v0.1): `infer_vibe()` tool calling Claude via MCP sampling API.
**Dropped**: MCP sampling was silently failing in Claude Desktop — always returned fallback vibe.

Current approach: Claude reasons directly in conversation. `get_coding_context` gives Claude the file/language/git/hour. Claude picks a search query itself based on the palette rules in the MCP server instructions. No separate inference tool.

### Playback

Original plan: Spotify Web API + `spotify:` URI.
**Dropped**: Spotify search endpoint requires app owner to have Premium (2024 API change).

Pivot 1: `webbrowser.open(youtube_music_url)` — worked but opened a new tab per track.
Pivot 2: Local HTTP controller at `localhost:8765` — serves an HTML page that manages one named YouTube Music window via `window.open()` + `playerWindow.location.href`.

### Track Search

Uses `yt-dlp` with `ytsearch{N}:query`. Filters to 1–8 min (removes compilations/mixes). Runs in a `ThreadPoolExecutor` with 20s timeout so it doesn't block the async event loop.

---

## Project Structure

```
vibedev-mcp/
├── DESIGN.md
├── README.md
├── .env.example
├── requirements.txt
├── server.py               ← FastMCP server, tool definitions, Claude instructions
├── vibe/
│   ├── context.py          ← filesystem scan, symbol extraction, git log
│   ├── music.py            ← yt-dlp track search (async, thread executor)
│   ├── player.py           ← queue, advance loop, state tracking
│   └── webplayer.py        ← local HTTP controller page (port 8765)
└── tests/
    ├── test_context.py
    └── test_vibe.py
```

---

## Key Pivots from v0.1

| What | Original Plan | What Actually Happened |
|---|---|---|
| Music source | Spotify Web API | YouTube Music via yt-dlp |
| Vibe inference | MCP sampling → Claude | Claude reasons directly in conversation |
| Playback | `spotify:` URI → desktop app | Local HTTP controller → YouTube Music window |
| Auth | Spotify OAuth2 PKCE | None required |

---

## Known Issues (v0.2)

1. **Tab management**: `window.open()` from JavaScript setInterval is blocked by browser popup blockers. The named window trick partially works but is unreliable — new tabs still appear on advance.
2. **Music picks**: Claude's query choice is inconsistent. Sometimes drifts to English (Nujabes, Bonobo) despite desi-first instructions, especially when context is ambiguous.
3. **Context scope**: `get_coding_context` finds the most recently modified file under WATCH_DIR. If you're working in VibeDev itself, it sees VibeDev. No editor session awareness.

---

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `LASTFM_API_KEY` | Optional | Tag validation (used in earlier version, now unused) |
| `SPOTIFY_CLIENT_ID` | No longer needed | Removed |
| `WATCH_DIR` | Recommended | Directory to scan. Default: home dir (slow). Set to your projects folder. |

---

## Out of Scope (v0.2)

- True single-tab playback without browser automation
- Per-developer taste learning
- VS Code extension / editor session awareness
- Apple Music / SoundCloud
- Volume control
- Mobile
