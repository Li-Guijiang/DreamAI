"""Render assets/brand/hero.svg to a high-frame-rate video.

The README hero used to be exported as a 24-frame WebP, which is 3 frames per
second over the 8-second loop — visibly stepped, and only 1x resolution. This
script renders the same SVG at 30 fps and 2x scale and encodes H.264, so the
motion is continuous and the edges stay sharp on retina screens.

Usage (repository root):

    python assets/brand/render_hero_video.py                # 1800x612, 30 fps
    python assets/brand/render_hero_video.py --fps 30 --scale 2 --crf 20

Requires a local Chrome or Edge and imageio-ffmpeg (both only for this script,
not for running the project).
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SVG = Path(__file__).resolve().parent / "hero.svg"
OUT = Path(__file__).resolve().parent / "hero.mp4"
PORT = 9444

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


# --- minimal DevTools client -------------------------------------------------

def _ws_connect(url: str) -> socket.socket:
    host_port, _, path = url[5:].partition("/")
    host, _, port = host_port.partition(":")
    sock = socket.create_connection((host, int(port)), timeout=60)
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall(
        (
            f"GET /{path} HTTP/1.1\r\nHost: {host_port}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).encode()
    )
    buf = b""
    while b"\r\n\r\n" not in buf:
        buf += sock.recv(4096)
    if b"101" not in buf.split(b"\r\n")[0]:
        raise RuntimeError("devtools handshake failed")
    return sock


def _ws_send(sock: socket.socket, payload: bytes) -> None:
    header = bytearray([0x81])
    n = len(payload)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header += struct.pack(">H", n)
    else:
        header.append(0x80 | 127)
        header += struct.pack(">Q", n)
    mask = os.urandom(4)
    header += mask
    sock.sendall(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))


def _ws_recv(sock: socket.socket) -> bytes:
    while True:
        head = sock.recv(2)
        if not head:
            raise RuntimeError("devtools connection closed")
        opcode, n = head[0] & 0x0F, head[1] & 0x7F
        if n == 126:
            n = struct.unpack(">H", sock.recv(2))[0]
        elif n == 127:
            n = struct.unpack(">Q", sock.recv(8))[0]
        data = b""
        while len(data) < n:
            data += sock.recv(n - len(data))
        if opcode == 0x9:
            sock.sendall(bytes([0x8A, 0x80]) + os.urandom(4))
            continue
        if opcode in (0x1, 0x2):
            return data


class DevTools:
    def __init__(self, url: str) -> None:
        self.sock = _ws_connect(url)
        self.seq = 0

    def call(self, method: str, params: dict | None = None) -> dict:
        self.seq += 1
        _ws_send(
            self.sock,
            json.dumps({"id": self.seq, "method": method, "params": params or {}}).encode(),
        )
        while True:
            msg = json.loads(_ws_recv(self.sock))
            if msg.get("id") == self.seq:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})


def _page_html(svg: str, width: int, height: int) -> str:
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
        "html,body{margin:0;padding:0;background:#0b0e17;overflow:hidden}"
        f"#stage{{width:{width}px;height:{height}px}}"
        f"#stage svg{{display:block;width:{width}px;height:{height}px}}"
        "</style></head><body><div id='stage'>" + svg + "</div></body></html>"
    )


def render(browser: str, width: int, height: int, fps: int, duration: float, crf: int) -> Path:
    import imageio_ffmpeg

    profile = Path(tempfile.mkdtemp(prefix="hero-frames-"))
    page = profile / "stage.html"
    page.write_text(
        _page_html(SVG.read_text(encoding="utf-8"), width, height), encoding="utf-8"
    )

    proc = subprocess.Popen(
        [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--no-default-browser-check",
            "--remote-allow-origins=*",
            f"--remote-debugging-port={PORT}",
            f"--user-data-dir={profile}",
            f"--window-size={width},{height}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        target = None
        for _ in range(60):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=2) as r:
                    for item in json.load(r):
                        if item.get("type") == "page" and item.get("webSocketDebuggerUrl"):
                            target = item["webSocketDebuggerUrl"]
                            break
                if target:
                    break
            except Exception:
                pass
            time.sleep(0.4)
        if not target:
            raise RuntimeError("no devtools target")

        dev = DevTools(target)
        dev.call("Page.enable")
        dev.call(
            "Emulation.setDeviceMetricsOverride",
            {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False},
        )
        dev.call("Page.navigate", {"url": page.resolve().as_uri()})
        for _ in range(60):
            state = dev.call(
                "Runtime.evaluate", {"expression": "document.readyState", "returnByValue": True}
            )
            if state.get("result", {}).get("value") == "complete":
                break
            time.sleep(0.2)
        time.sleep(1.0)

        dev.call(
            "Runtime.evaluate",
            {
                "expression": """
                (() => {
                  const svg = document.querySelector('#stage svg');
                  window.__svg = svg;
                  window.__anims = document.getAnimations();
                  window.__anims.forEach(a => a.pause());
                  if (svg && svg.pauseAnimations) svg.pauseAnimations();
                  return window.__anims.length;
                })()
                """,
                "returnByValue": True,
            },
        )

        total = int(round(duration * fps))
        encoder = subprocess.Popen(
            [
                imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
                "-f", "image2pipe", "-framerate", str(fps), "-i", "-",
                "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        for i in range(total):
            t = i / fps
            dev.call(
                "Runtime.evaluate",
                {
                    "expression": f"""
                    (() => {{
                      window.__anims.forEach(a => {{ a.currentTime = {t * 1000}; }});
                      if (window.__svg && window.__svg.setCurrentTime) window.__svg.setCurrentTime({t});
                      return true;
                    }})()
                    """,
                    "returnByValue": True,
                },
            )
            shot = dev.call("Page.captureScreenshot", {"format": "png"})
            encoder.stdin.write(base64.b64decode(shot["data"]))
            if i % 30 == 0:
                print(f"  frame {i}/{total}", flush=True)
        encoder.stdin.close()
        encoder.wait()
        dev.call("Browser.close")
    finally:
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
    return OUT


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=1800)
    ap.add_argument("--height", type=int, default=612)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--duration", type=float, default=8.0)
    ap.add_argument("--crf", type=int, default=20)
    args = ap.parse_args()

    for browser in BROWSERS:
        if Path(browser).exists():
            out = render(browser, args.width, args.height, args.fps, args.duration, args.crf)
            print(f"{out.name}: {out.stat().st_size / 1024:.0f} KB "
                  f"({args.width}x{args.height}, {args.fps} fps, crf {args.crf})")
            return
    sys.exit("no Chrome or Edge found")


if __name__ == "__main__":
    main()
