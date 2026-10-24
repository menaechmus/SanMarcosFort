"""Smoke-test the web export in headless Chrome or Edge.

Serves build/web, opens a copy of index.html that passes extra engine arguments (the
autoplay bot by default), keeps the page "loading" for --seconds of real time so the game
runs, then saves a screenshot and prints the browser console lines that matter.

Usage (standard library only):
    python -I tools/web_smoke_test.py [--seconds 25] [--out build/shots/web.png]
"""

import argparse
import http.server
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
HOLD_PATH = "/__hold"
TEST_PAGE = "/__smoke.html"


def make_handler(web_dir: Path, page: bytes, hold_seconds: float):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(web_dir), **kwargs)

        def do_GET(self):
            if self.path.startswith(HOLD_PATH):
                # Delays the page's load event, so the screenshot waits for the game.
                time.sleep(hold_seconds)
                self._send(b"GIF89a\x01\x00\x01\x00\x00\x00\x00;", "image/gif")
            elif self.path.startswith(TEST_PAGE):
                self._send(page, "text/html")
            else:
                super().do_GET()

        def _send(self, body: bytes, content_type: str):
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    return Handler


def build_page(index_html: str, engine_args: list) -> bytes:
    html, count = re.subn(r'"args":\s*\[\]', '"args":' + json.dumps(engine_args), index_html)
    if count == 0:
        raise SystemExit("Could not find the engine args in index.html")
    hold = f'<img src="{HOLD_PATH}" style="position:absolute;width:1px;height:1px;opacity:0">'
    return html.replace("</body>", hold + "</body>").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seconds", type=float, default=25.0, help="real seconds to let the game run")
    parser.add_argument("--out", default="build/shots/web.png")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--args", default="--autoplay --timescale=3", help="extra engine arguments")
    options = parser.parse_args()

    web_dir = PROJECT / "build" / "web"
    index = web_dir / "index.html"
    if not index.exists():
        raise SystemExit("No web export found; run tools/export_all.ps1 Web first")
    browser = next((b for b in BROWSERS if os.path.exists(b)), None)
    if browser is None:
        raise SystemExit("Chrome or Edge not found")

    page = build_page(index.read_text(encoding="utf-8"), ["--"] + options.args.split())
    handler = make_handler(web_dir, page, options.seconds)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", options.port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    out = (PROJECT / options.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    profile = tempfile.mkdtemp(prefix="smoke-profile-")
    cmd = [
        browser, "--headless=new", f"--user-data-dir={profile}", "--no-first-run",
        "--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--window-size=1280,720",
        "--enable-logging=stderr", "--v=0", f"--screenshot={out}",
        f"http://127.0.0.1:{options.port}{TEST_PAGE}",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                                timeout=options.seconds + 120)
    finally:
        server.shutdown()
        shutil.rmtree(profile, ignore_errors=True)

    console = [line for line in result.stderr.splitlines() if "CONSOLE" in line or "console" in line]
    interesting = [line for line in console if re.search(r"error|warn|report|capture|exception", line, re.I)]
    print(f"browser: {Path(browser).name}, exit {result.returncode}")
    print(f"console lines: {len(console)}, notable: {len(interesting)}")
    for line in interesting[:40]:
        print("  " + line[-300:])
    print(f"screenshot: {out} ({'ok' if out.exists() else 'missing'})")
    return 0 if out.exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
