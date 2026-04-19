# VibeDev

> Mood-matched Indian/desi music that plays itself while you code — powered by Claude Desktop and MCP.

VibeDev is a local MCP server that reads what you're actively working on, picks artists from a curated pool of Indian subcontinent music, finds real tracks on YouTube Music via `yt-dlp`, and keeps the queue going automatically. No playlist curation. No manually asking for songs. It just runs.

---

## What it does

1. Reads your active coding context — open VS Code folder, PowerShell history, file language, symbols, time of day
2. Maps the context to a vibe category (late night, intense, deep grind, energized, focus, chill)
3. Picks 3 artists from that category and searches YouTube Music for real tracks
4. Queues a mixed ~12-track playlist and opens it in a dedicated browser window
5. Auto-advances before each song ends, and when the queue finishes, does a fresh vibe check and loads new music

Everything after the first "play music" prompt is autonomous.

---

## Music palette

Desi-first. The full palette covers:

| Vibe | Triggered by | Artists |
|---|---|---|
| `late_night` | After 10pm / before 10am | Jagjit Singh, Nusrat Fateh Ali Khan, Ghulam Ali, Mehdi Hassan, Abida Parveen, Farida Khanum, Arijit Singh, KK, Atif Aslam |
| `intense` | Tests, debugging, Rust, Go | Seedhe Maut, Prabh Deep, Kr$na, Emiway Bantai, Hanumankind, MC Stan, DIVINE, Raftaar, Young Stunners, Talha Anjum |
| `deep_grind` | ML/model/training code | Karan Aujla, Sidhu Moosewala, Shubh, Bohemia, Coke Studio Pakistan, Strings, Junoon, Ali Zafar |
| `energized` | App/server/index/main files | Diljit Dosanjh, Badshah, Yo Yo Honey Singh, Nucleya, Benny Dayal, Ritviz, Anirudh Ravichander |
| `focus` | Python, TypeScript, JavaScript | A.R. Rahman, Ilaiyaraaja, Amit Trivedi, Pritam, Shankar Ehsaan Loy, Ravi Shankar, Zakir Hussain, Hariprasad Chaurasia |
| `chill` | Docs, YAML, config, morning | AP Dhillon, Talwiinder, Prateek Kuhad, When Chai Met Toast, The Local Train, Ali Sethi, Arooj Aftab, Lucky Ali, Kishore Kumar |

Each session picks 3 artists from the matching category, takes up to 4 tracks each, and queues a shuffled mix. Artists rotate so you don't hear the same one twice in a row.

---

## How the agentic loop works

The server exposes 5 MCP tools to Claude Desktop:

| Tool | What it does |
|---|---|
| `get_coding_context()` | Scans your active project, returns context + `suggested_queries` (3 artists) + `next_action` |
| `search_tracks(query, fallback_query)` | YouTube search via `yt-dlp`, filters to 1–8 min tracks, returns YouTube Music URLs |
| `queue_tracks(tracks)` | Loads tracks, opens first song, starts background auto-advance |
| `skip_track()` | Skips to next track |
| `get_now_playing()` | Current track, elapsed/remaining time, queue position |

The `get_coding_context()` response includes a `next_action` field that tells Claude exactly what to do next — which queries to search, how many tracks to take per artist, how to combine them. This keeps Claude on the right artists instead of improvising.

---

## Context detection

VibeDev checks these sources in priority order to find what you're working on:

1. VS Code's last active window (`%APPDATA%\Code\User\globalStorage\storage.json`)
2. Recent absolute `cd` commands from PowerShell history
3. `WATCH_DIR` env var / `.env` file
4. Home directory as fallback

The scan has a 2-second deadline and runs in a thread so it never blocks the MCP server.

---

## Playback

VibeDev launches YouTube Music in a dedicated Edge or Chrome app window (`--app` mode) with a persistent profile at `~/.vibedev/edge-profile`. Each track opens a fresh window; the previous one is terminated.

First run: sign into YouTube Music in the VibeDev window once. That login persists.

The auto-advance loop checks every 3 seconds and opens the next track ~10 seconds before the current one ends. When the last track in the queue is about to finish, it re-runs context detection, picks 3 new artists, and loads a fresh queue — music never stops.

---

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Claude Desktop

On Windows, edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vibedev": {
      "command": "C:\\Path\\To\\Python\\python.exe",
      "args": ["C:\\Path\\To\\VibeDev\\server.py"],
      "env": {
        "WATCH_DIR": "C:\\Users\\YourName\\Projects",
        "APPDATA": "C:\\Users\\YourName\\AppData\\Roaming",
        "USERPROFILE": "C:\\Users\\YourName"
      }
    }
  }
}
```

`APPDATA` and `USERPROFILE` are needed because Claude Desktop spawns the server in a minimal environment that may not inherit them.

Restart Claude Desktop after editing.

### 3. Play music

```
Play music for what I'm coding.
```

Claude calls `get_coding_context()`, reads `next_action`, searches the suggested artists, and queues a mixed playlist. After that it runs on its own.

---

## Smoke checks

Verify server imports and tools are registered:

```bash
python -c "import asyncio, server; print([t.name for t in asyncio.run(server.mcp.list_tools())])"
```

Test context detection:

```bash
python -c "from vibe.context import get_coding_context; import json; print(json.dumps(get_coding_context('C:/path/to/your/project'), indent=2))"
```

Test track search:

```bash
python -c "import asyncio; from vibe.music import search_tracks; print(asyncio.run(search_tracks('AP Dhillon', 'Karan Aujla')))"
```

---

## Project structure

```
VibeDev/
├── server.py          # FastMCP server and tool definitions
├── vibe/
│   ├── context.py     # Project detection, file scan, artist pool, vibe picker
│   ├── music.py       # yt-dlp search and duration filtering
│   ├── player.py      # Queue state, auto-advance, auto-refresh
│   └── webplayer.py   # Edge/Chrome app-window launcher
├── tests/
├── requirements.txt
└── .env               # WATCH_DIR (optional, not committed)
```

---

## Notes

- Requires Edge or Chrome. Falls back to `webbrowser.open()` if neither is found.
- `yt-dlp` needs network access to search YouTube. Results vary with YouTube's behavior.
- The queue advance is time-based (track duration from yt-dlp metadata), not browser playback state. If autoplay is blocked by YouTube, the next window still opens on schedule.
- No Spotify. No Last.fm. No API keys required.
