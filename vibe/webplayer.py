"""
Local HTTP controller page — manages a single YouTube Music window.

Instead of calling webbrowser.open() per track (which creates a new tab),
we serve a controller page at localhost:8765. That page opens YouTube Music
in a named window once, then navigates it for each subsequent track.
Result: one persistent YouTube Music tab, no accumulation.
"""

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8765

_state: dict = {"url": None, "title": None, "uploader": None}
_server: HTTPServer | None = None

_CONTROLLER_HTML = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>VibeDev</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #111;
      color: #eee;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      gap: 12px;
    }
    #label { font-size: 11px; letter-spacing: 2px; text-transform: uppercase; color: #666; }
    #title { font-size: 20px; font-weight: 600; color: #fff; text-align: center; max-width: 500px; }
    #artist { font-size: 14px; color: #aaa; }
    #dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: #1db954; margin-top: 8px;
      animation: pulse 2s infinite;
    }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
  </style>
</head>
<body>
  <div id="label">VIBEDEV</div>
  <div id="title">Waiting for track...</div>
  <div id="artist"></div>
  <div id="dot"></div>
  <script>
    let playerWindow = null;
    let lastUrl = '';

    async function check() {
      try {
        const r = await fetch('/current');
        const d = await r.json();
        if (d.url && d.url !== lastUrl) {
          lastUrl = d.url;
          document.getElementById('title').textContent = d.title || '';
          document.getElementById('artist').textContent = d.uploader || '';
          if (!playerWindow || playerWindow.closed) {
            playerWindow = window.open(d.url, 'vibedev-player');
          } else {
            playerWindow.location.href = d.url;
          }
        }
      } catch(e) {}
    }

    check();
    setInterval(check, 3000);
  </script>
</body>
</html>
"""


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # suppress request logs

    def do_GET(self):
        if self.path == "/current":
            body = json.dumps(_state).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            body = _CONTROLLER_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


def start():
    """Start the controller server and open it in the browser (idempotent)."""
    global _server
    if _server is not None:
        return
    _server = HTTPServer(("127.0.0.1", PORT), _Handler)
    threading.Thread(target=_server.serve_forever, daemon=True).start()
    webbrowser.open(f"http://127.0.0.1:{PORT}")


def update(url: str, title: str, uploader: str):
    """Update the current track — controller page picks it up within 3s."""
    _state["url"] = url
    _state["title"] = title
    _state["uploader"] = uploader
