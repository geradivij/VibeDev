"""
infer_vibe(context, ctx) — passes coding context to Claude via MCP sampling
and returns a structured vibe JSON.

Claude does all reasoning — no hardcoded language→genre rules here.
"""

import json
import re

from mcp.types import SamplingMessage, TextContent

_SYSTEM_PROMPT = """\
You are a music curator AI. Given a developer's current coding context,
you infer the emotional vibe of their work and recommend music to play.

Your music palette (in priority order):
1. Punjabi/Hindi artists: AP Dhillon, Shubh, Karan Aujla, Sidhu Moosewala, Diljit Dosanjh, DIVINE, Badshah
2. English hip-hop: Drake, Travis Scott, Kendrick Lamar, J. Cole — matched to vibe intensity
3. English lo-fi/ambient: only as last resort

Rules:
- Always try desi music first.
- For lastfm_tags, ONLY use tags that exist on Last.fm. Valid desi tags: "desi beats", "punjabi hip hop", "desi hip hop". Valid English tags: "lo-fi hip hop", "hip hop", "rap".
- spotify_query: a YouTube search string to find a SINGLE SONG (2-5 min). Name a specific artist and vibe. Example: "AP Dhillon Brown Munde", "Shubh We Rollin", "Karan Aujla 8 Ball"
- fallback_query: a specific English song if no desi match. Example: "Drake Nonstop", "Travis Scott Goosebumps"
- energy: 0.0 (calm) → 1.0 (intense)
- valence: 0.0 (dark/tense) → 1.0 (bright/happy)
- focus: one of "deep", "flow", "hype", "chill", "scattered"
- primary_language: one of "hindi", "punjabi", "english"
- label: evocative vibe label ≤5 words

Respond with ONLY a JSON object — no prose, no markdown fences.\
"""

_USER_TEMPLATE = """\
Coding context:
- Language: {language}
- File: {filename}
- Symbols: {symbols}
- Last git commit: {git_message}
- Hour of day: {hour_of_day}:00

What's the vibe? Return JSON with keys:
energy, valence, focus, primary_language, lastfm_tags, spotify_query, fallback_query, label\
"""

_FALLBACK_VIBE = {
    "energy": 0.6,
    "valence": 0.6,
    "focus": "flow",
    "primary_language": "punjabi",
    "lastfm_tags": ["desi beats", "punjabi hip hop"],
    "spotify_query": "AP Dhillon Brown Munde official",
    "fallback_query": "Drake Nonstop official audio",
    "label": "steady flow",
}


def _build_user_message(context: dict) -> str:
    symbols_str = (
        ", ".join(context.get("symbols", [])) or "none detected"
    )
    git_msg = context.get("git_message") or "no recent commit"
    return _USER_TEMPLATE.format(
        language=context.get("language", "unknown"),
        filename=context.get("filename") or "unknown",
        symbols=symbols_str,
        git_message=git_msg,
        hour_of_day=context.get("hour_of_day", 12),
    )


def _parse_vibe_json(text: str) -> dict:
    """Extract and validate JSON from Claude's response."""
    # Strip any accidental markdown fences
    text = re.sub(r"```(?:json)?", "", text).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find a JSON object anywhere in the text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            return _FALLBACK_VIBE.copy()

    # Validate required keys and types, fill defaults for missing
    vibe = _FALLBACK_VIBE.copy()
    vibe.update({k: v for k, v in data.items() if k in _FALLBACK_VIBE})

    # Clamp numeric fields
    vibe["energy"] = max(0.0, min(1.0, float(vibe["energy"])))
    vibe["valence"] = max(0.0, min(1.0, float(vibe["valence"])))

    if not isinstance(vibe["lastfm_tags"], list):
        vibe["lastfm_tags"] = [str(vibe["lastfm_tags"])]

    return vibe


async def infer_vibe(context: dict, ctx) -> dict:
    """
    Ask Claude (via MCP sampling) to infer a music vibe from coding context.

    ctx is the fastmcp Context object — it provides ctx.sample() for
    MCP sampling requests back to the host (Claude Desktop).

    Returns a vibe dict with keys:
        energy, valence, focus, primary_language, lastfm_tags,
        spotify_query, fallback_query, label
    """
    user_message = _build_user_message(context)

    messages = [
        SamplingMessage(
            role="user",
            content=TextContent(type="text", text=user_message),
        )
    ]

    try:
        result = await ctx.sample(
            messages=messages,
            system_prompt=_SYSTEM_PROMPT,
            max_tokens=512,
        )
        response_text = result.text if hasattr(result, "text") else str(result)
        return _parse_vibe_json(response_text)
    except Exception:
        # If sampling fails (e.g. no host), return a sensible fallback
        return _FALLBACK_VIBE.copy()
