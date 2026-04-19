# VibeDev MCP

> Ambient music that matches what you're building.

An MCP server that reads your active coding context and autonomously opens a matching Spotify playlist. Claude does the vibe reasoning — no hardcoded rules. No Spotify Premium required.

**Music palette:** Hindi lo-fi · Punjabi trap/beats · Bollywood instrumentals → English hip-hop → English ambient/lo-fi

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Get API keys

- **Last.fm** (free): https://www.last.fm/api/account/create
- **Spotify app** (free): https://developer.spotify.com/dashboard
  - Set redirect URI to `http://localhost:8888/callback` in your app settings
  - Enable "Web API" scope in the dashboard
  - You need both **Client ID** and **Client Secret** for playlist search

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in your keys
```

### 4. Add to Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "vibedev": {
      "command": "python",
      "args": ["/absolute/path/to/vibedev-mcp/server.py"]
    }
  }
}
```

Restart Claude Desktop.

---

## The 5 Tools

| Tool | What it does |
|---|---|
| `get_coding_context()` | Scans filesystem for most recently modified source file, extracts language/symbols/git message |
| `infer_vibe(context)` | Claude reasons over context → returns vibe JSON (energy, mood, tags, queries) |
| `search_playlist(vibe)` | Last.fm validates tags → Spotify finds a playlist → returns URI |
| `open_playlist(uri)` | Opens `spotify:` URI in desktop app (cross-platform, no Premium needed) |
| `get_now_playing()` | Polls Spotify currently-playing endpoint (free tier, metadata only) |

### Example agentic loop

```
"Play music that matches what I'm working on"

→ get_coding_context()   → { language: python, filename: train.py, symbols: [ModelTrainer, fit], git_message: "fix: loss converging", hour: 23 }
→ infer_vibe(context)    → { energy: 0.75, focus: "deep", label: "late-night ML grind", spotify_query: "punjabi trap coding playlist" }
→ search_playlist(vibe)  → { playlist_uri: "spotify:playlist:...", playlist_name: "Punjabi Trap 2024" }
→ open_playlist(uri)     → opens Spotify desktop app
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `LASTFM_API_KEY` | Optional | Enables Last.fm tag validation. Without it, Claude's tags are used directly. |
| `SPOTIFY_CLIENT_ID` | Required | Your Spotify app's client ID |
| `SPOTIFY_CLIENT_SECRET` | Required for search | Client secret for playlist search (client credentials flow) |
| `SPOTIFY_REDIRECT_URI` | Optional | Defaults to `http://localhost:8888/callback` |
| `WATCH_DIR` | Optional | Directory to scan for active file. Defaults to home directory. |

---

## Running Tests

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

---

## How It Works

**Editor-agnostic file detection** — watches filesystem modification timestamps instead of a VS Code extension. Works with any editor, zero plugin install.

**Claude does vibe reasoning** — `infer_vibe()` passes context to Claude via MCP sampling and asks for structured JSON. No if/else genre mapping. The interesting part.

**Last.fm bridges the recommendations gap** — Spotify deprecated audio features and recommendations APIs in 2024. Last.fm fills that: free, tag-based, community-curated. Claude picks tags, Last.fm validates them, Spotify finds the playlist.

**No Premium required** — playback via `spotify:` URI launch means we never touch the Spotify playback API. The OS opens Spotify like clicking a link. Free users shuffle-play, Premium users get ordered playback.

---

## Project Structure

```
vibedev-mcp/
├── DESIGN.md           ← architecture and decisions
├── README.md
├── .env.example
├── requirements.txt
├── server.py           ← MCP server, all 5 tool definitions
├── vibe/
│   ├── context.py      ← filesystem scan, symbol extraction, git message
│   ├── infer.py        ← MCP sampling → Claude vibe reasoning
│   ├── music.py        ← Last.fm tag validation + Spotify playlist search
│   └── player.py       ← URI launch (cross-platform) + now playing
└── tests/
    ├── test_context.py
    └── test_vibe.py
```
