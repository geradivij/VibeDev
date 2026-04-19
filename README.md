# VibeDev MCP

Ambient Indian/desi music for whatever you are coding.

VibeDev is a local MCP server for Claude Desktop. It reads coding context from your machine, chooses a matching artist/search query, finds real tracks with `yt-dlp`, and queues them in a dedicated browser app window pointed at YouTube Music.

The current implementation is YouTube Music based. It does not use Spotify.

## Current Flow

```text
Claude Desktop
  -> get_coding_context()
  -> follow next_action exactly
  -> search_tracks(query=suggested_query, fallback_query="AP Dhillon")
  -> queue_tracks(tracks)
  -> YouTube Music opens in a dedicated Edge/Chrome app window
```

`get_coding_context()` returns both `suggested_query` and `next_action`. The server instructions tell Claude to start with context detection and then follow `next_action` exactly, so the model does not replace the selected artist with its own choice.

## Music Palette

VibeDev is desi-first.

Primary artists include Punjabi, Hindi, Pakistani, ghazal, sufi, indie, film-score, classical, and desi rap artists. Examples include AP Dhillon, Shubh, Karan Aujla, Sidhu Moosewala, DIVINE, Seedhe Maut, Talha Anjum, Diljit Dosanjh, Badshah, Arijit Singh, Talwiinder, A.R. Rahman, Nusrat Fateh Ali Khan, Jagjit Singh, Abida Parveen, Coke Studio Pakistan, Prateek Kuhad, The Local Train, Ravi Shankar, and Zakir Hussain.

The context picker maps coding context to rough categories:

| Context signal | Category | Example artists |
|---|---|---|
| Late night | `late_night` | Jagjit Singh, Ghulam Ali, Mehdi Hassan, Nusrat Fateh Ali Khan, Abida Parveen, Arijit Singh |
| Tests, debugging, Rust, Go | `intense` | Seedhe Maut, Prabh Deep, Kr$na, Emiway Bantai, Young Stunners, DIVINE, Raftaar |
| ML/training/model work | `deep_grind` | Karan Aujla, Sidhu Moosewala, Shubh, Bohemia, Coke Studio Pakistan, Junoon |
| App/server/main files | `energized` | Diljit Dosanjh, Badshah, Yo Yo Honey Singh, Nucleya, Ritviz, Shankar Ehsaan Loy |
| Python/TypeScript/JavaScript flow | `focus` | A.R. Rahman, Amit Trivedi, Ilaiyaraaja, Pritam, Ravi Shankar, Zakir Hussain |
| Docs/config/chill work | `chill` | AP Dhillon, Talwiinder, Prateek Kuhad, The Local Train, Ali Sethi, Lucky Ali |

## Tools

| Tool | What it does |
|---|---|
| `get_coding_context(watch_dir="")` | Finds the most recently modified source file and returns language, filename, symbols, hour, active project, editor source, `suggested_query`, and `next_action`. |
| `search_tracks(query, fallback_query="lo-fi hip hop focus")` | Uses `yt-dlp` YouTube search, filters to 1-8 minute tracks, and returns YouTube Music URLs. |
| `queue_tracks(tracks)` | Loads a track list, opens the first song, and starts a background auto-advance loop. |
| `skip_track()` | Moves to the next track in the queue. |
| `get_now_playing()` | Reports current track, elapsed time, remaining time, and queue position. |

## Context Detection

VibeDev tries to infer what project you are actively working in. It checks these sources in order:

1. An explicit `watch_dir` argument, if provided.
2. VS Code's last active window from `%APPDATA%\Code\User\globalStorage\storage.json`.
3. Recent absolute `cd` commands from PowerShell history.
4. `WATCH_DIR` from `.env`.
5. Your home directory as a final fallback.

The scan is intentionally shallow and time-limited so Claude Desktop does not hang while waiting for context.

## Playback

Playback is handled by `vibe/webplayer.py`.

The player looks for Edge or Chrome, then launches YouTube Music with:

- `--app=<youtube_music_url>`
- a dedicated browser profile at `~/.vibedev/edge-profile`
- `--autoplay-policy=no-user-gesture-required`

The dedicated profile matters. On first run, you may need to sign into YouTube Music inside the VibeDev app window once. That login should persist for later runs.

Each track change terminates the previous app-window process and opens the next track in a fresh app window using the same profile.

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Create `.env` in the project root:

```env
WATCH_DIR=C:\Users\gerad\Projects
```

`WATCH_DIR` is recommended, but the server can also use VS Code and PowerShell history to find the active project.

Spotify credentials are not needed. Last.fm is not used by the current flow.

### 3. Add to Claude Desktop

On Windows, edit:

```text
%APPDATA%\Claude\claude_desktop_config.json
```

Use an absolute path to this repo's `server.py`:

```json
{
  "mcpServers": {
    "vibedev": {
      "command": "python",
      "args": ["C:\\Users\\gerad\\Projects\\VibeDev\\server.py"]
    }
  }
}
```

Restart Claude Desktop after editing the config.

### 4. Ask Claude to play music

Example:

```text
Play music for what I'm coding.
```

Claude should call:

1. `get_coding_context()`
2. Follow the returned `next_action`, which currently means `search_tracks(query=<suggested_query>, fallback_query="AP Dhillon")`
3. `queue_tracks(tracks=<tracks from search_tracks>)`

## Local Smoke Checks

Check that the server imports and exposes tools:

```bash
python -c "import asyncio, server; print([t.name for t in asyncio.run(server.mcp.list_tools())])"
```

Check context detection for this repo:

```bash
python -c "from vibe.context import get_coding_context; print(get_coding_context('C:/Users/gerad/Projects/VibeDev'))"
```

The output should include `suggested_query` and `next_action`.

Check track search:

```bash
python -c "import asyncio; from vibe.music import search_tracks; print(asyncio.run(search_tracks('AP Dhillon', 'lo-fi hip hop focus')))"
```

The track search needs network access because `yt-dlp` queries YouTube.

## Running Tests

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

The unit tests cover older context and vibe parsing behavior. The active MCP flow is better checked with the smoke commands above.

## Project Structure

```text
VibeDev/
|-- .claude/
|   `-- settings.local.json # Local Claude permissions, currently allows WebSearch
|-- DESIGN.md
|-- README.md
|-- requirements.txt
|-- server.py              # FastMCP server and tool definitions
|-- vibe/
|   |-- context.py         # Active project detection, source scan, artist picker
|   |-- music.py           # yt-dlp search and duration filtering
|   |-- player.py          # Queue state, skip, auto-advance
|   |-- webplayer.py       # Edge/Chrome app-window launcher
|   |-- infer.py           # Older MCP sampling experiment, not exposed by server.py
|   `-- __init__.py
`-- tests/
    |-- test_context.py
    `-- test_vibe.py
```

## Known Issues

- `test_live.py` is stale and still references an older `play_track` API.
- `infer.py` is not part of the active server flow.
- Browser autoplay can still depend on the browser, YouTube Music session state, and whether the dedicated profile has been signed in.
- `yt-dlp` search can fail if network access is blocked or YouTube changes behavior.
- The current queue advances based on reported video duration, not actual browser playback state.

## Notes

`.env`, `.cache`, Python bytecode, pytest caches, and temporary files are ignored by `.gitignore`. Keep local auth/session files out of commits.
