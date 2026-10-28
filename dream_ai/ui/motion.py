"""Small, dependency-free terminal animation toolkit.

Dream AI's terminal should feel like the same universe as the website without
making automation brittle. Every visual effect therefore:

* only runs when stdout is a real TTY and animations are enabled;
* respects ``NO_COLOR`` and ``TERM=dumb``;
* can be disabled with ``--no-animation`` / ``DREAMAI_ANIMATIONS=false``;
* never changes the text content that is written.

The implementation uses standard ANSI sequences and a single short-lived
spinner thread. Nothing else in the agent imports it.
"""

from __future__ import annotations

import contextlib
import os
import sys
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TextIO

BANNER = r"""
  ____  ____  __  __    _    __  __ _____
 |  _ \|  _ \|  \/  |  / \  |  \/  | ____|
 | |  \ | |_) | |\/| | / _ \ | |\/| |  _|
 | |__| |  _ <| |  | |/ ___ \| |  | | |___
 |_____/|_| \_\_|  |_/_/   \_\_|  |_|_____|
"""

_SPINNER = ("◐", "◓", "◑", "◒")
_PHASE_COLORS = {
    "think": "\x1b[38;2;124;156;255m",
    "plan": "\x1b[38;2;183;156;255m",
    "act": "\x1b[38;2;94;234;212m",
    "observe": "\x1b[38;2;243;199;123m",
    "reflect": "\x1b[38;2;240;166;200m",
    "confirm": "\x1b[38;2;255;123;134m",
    "done": "\x1b[38;2;94;234;212m",
    "abort": "\x1b[38;2;255;123;134m",
}
_RESET = "\x1b[0m"
_DIM = "\x1b[2m"
_CLEAR_LINE = "\r\x1b[2K"


@dataclass(frozen=True)
class MotionSettings:
    """The user-facing motion switches."""

    enabled: bool = True
    speed: float = 1.0

    @classmethod
    def from_values(cls, enabled: bool, speed: float) -> MotionSettings:
        return cls(enabled=enabled, speed=max(0.25, min(4.0, speed)))


def prepare_output(stream: TextIO | None = None) -> None:
    """Prefer UTF-8 when stdout is redirected (for example to a log file).

    Interactive terminals keep their native encoding. This helper is safe to
    call more than once and never raises when a stream cannot be reconfigured.
    """
    target = sys.stdout if stream is None else stream
    try:
        is_tty = bool(target.isatty())
    except (AttributeError, OSError):
        is_tty = False
    if is_tty:
        return
    try:
        target.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        return


def _enable_windows_ansi() -> None:
    """Best-effort virtual-terminal mode for the legacy Windows console."""
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except (AttributeError, OSError):  # pragma: no cover - platform dependent
        return


def supports_animation(stream: TextIO, requested: bool = True) -> bool:
    """Return whether animated output is safe for this stream."""
    if not requested:
        return False
    raw = os.getenv("DREAMAI_ANIMATIONS", "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if os.getenv("TERM", "").strip().lower() == "dumb":
        return False
    try:
        return bool(stream.isatty())
    except (AttributeError, OSError):
        return False


@dataclass
class Console:
    """Styled terminal output with graceful plain-text fallbacks."""

    enabled: bool = True
    speed: float = 1.0
    stream: TextIO = field(default_factory=lambda: sys.stdout)
    animate: bool = field(init=False)
    color: bool = field(init=False)

    def __post_init__(self) -> None:
        self.speed = max(0.25, min(4.0, float(self.speed)))
        self._prepare_stream()
        self.animate = supports_animation(self.stream, self.enabled) and not os.getenv("NO_COLOR")
        self.color = self.animate
        if self.color:
            _enable_windows_ansi()

    def _prepare_stream(self) -> None:
        """Use UTF-8 for redirected output, where possible.

        Windows can select a legacy code page for pipes even when the content
        is full of Chinese and box-drawing characters. Prefer UTF-8 for logs;
        interactive terminals keep their native encoding and use the safe-write
        fallback below for unsupported glyphs.
        """
        if self.stream is not sys.stdout:
            return
        prepare_output(self.stream)

    # -- low-level helpers -------------------------------------------------

    def _paint(self, text: str, code: str) -> str:
        return f"{code}{text}{_RESET}" if self.color else text

    def write(self, text: str) -> None:
        try:
            self.stream.write(text)
        except UnicodeEncodeError:
            encoding = getattr(self.stream, "encoding", None) or "utf-8"
            self.stream.write(text.encode(encoding, errors="replace").decode(encoding))
        self.stream.flush()

    def line(self, text: str = "") -> None:
        self.write(f"{text}\n")

    def blank(self) -> None:
        self.line()

    # -- semantic styles ---------------------------------------------------

    def accent(self, text: str) -> str:
        return self._paint(text, "\x1b[38;2;124;156;255m")

    def muted(self, text: str) -> str:
        return self._paint(text, "\x1b[38;2;118;126;144m")

    def success(self, text: str) -> str:
        return self._paint(text, "\x1b[38;2;94;234;212m")

    def warn(self, text: str) -> str:
        return self._paint(text, "\x1b[38;2;243;199;123m")

    def error(self, text: str) -> str:
        return self._paint(text, "\x1b[38;2;255;123;134m")

    # -- blocks ------------------------------------------------------------

    def logo(self) -> None:
        """Print the wordmark with a tiny per-line reveal."""
        lines = BANNER.strip("\n").splitlines()
        gradient = (
            "\x1b[38;2;94;234;212m",
            "\x1b[38;2;116;207;228m",
            "\x1b[38;2;124;156;255m",
            "\x1b[38;2;151;156;255m",
            "\x1b[38;2;183;156;255m",
        )
        for index, line in enumerate(lines):
            painted = self._paint(line, gradient[index % len(gradient)])
            self.line(painted)
            if self.animate:
                time.sleep(0.025 / self.speed)

    def intro(self, version: str, provider: str, model: str, offline: bool) -> None:
        """The small launch sequence shown once per session."""
        self.logo()
        mode = "offline demo" if offline else "hosted"
        self.line(
            f"  {self.accent('✦ DREAM AI')}  "
            f"{self.muted('// one shared dream')}  "
            f"{self.muted(f'v{version} · {mode}')}"
        )
        self.line(f"  {self.muted('provider')} {provider}  {self.muted('model')} {model}")
        self.line(self.muted("  ─" * 26))
        if self.animate:
            self.type_text("  connecting the universe", speed=0.019)
            self.line()
        self.blank()

    def type_text(self, text: str, *, speed: float = 0.0035) -> None:
        """Reveal text character-by-character inside the current line."""
        if not self.animate:
            self.write(text)
            return
        length = max(1, len(text))
        budget = 1.55 / max(0.4, self.speed)
        delay = max(0.0009, min(speed / max(0.4, self.speed), budget / length))
        for character in text:
            self.write(character)
            if character not in {"\n", "\r"}:
                time.sleep(delay)

    def reply(self, text: str, *, prefix: str = "dream-ai › ") -> None:
        """Print an assistant answer with an animated reveal."""
        if not self.animate:
            self.line(f"{prefix}{text}")
            self.blank()
            return
        self.write(self.accent(prefix))
        self.type_text(text)
        self.line()
        self.blank()

    def user_prompt(self) -> str:
        if self.color:
            return self._paint("you › ", "\x1b[38;2;94;234;212m")
        return "you › "

    def event(self, phase: str, step: str, content: str) -> None:
        """Render one autonomy trace line."""
        colour = _PHASE_COLORS.get(phase, _PHASE_COLORS["think"])
        tag = f"[{phase}]"
        if self.color:
            tag = f"{colour}{tag}{_RESET}"
            content = f"{_DIM}{content}{_RESET}"
        self.line(f"  {tag} {self.muted(step)}: {content}")

    def trace_line(self, text: str) -> None:
        self.line(f"  {self.muted(text)}")

    @contextlib.contextmanager
    def status(self, label: str) -> Iterator[None]:
        """Show a compact spinner while a blocking call runs."""
        if not self.animate:
            yield
            return

        stop = threading.Event()

        def spin() -> None:
            start = time.monotonic()
            frame = 0
            while not stop.is_set():
                elapsed = time.monotonic() - start
                glyph = _SPINNER[frame % len(_SPINNER)]
                text = (
                    f"{_CLEAR_LINE}"
                    f"\x1b[38;2;124;156;255m{glyph}{_RESET} "
                    f"{label} {_DIM}{elapsed:4.1f}s{_RESET}"
                )
                self.write(text)
                frame += 1
                stop.wait(0.085 / max(0.5, self.speed))

        thread = threading.Thread(target=spin, name="dream-ai-spinner", daemon=True)
        thread.start()
        try:
            yield
        finally:
            stop.set()
            thread.join(timeout=1)
            self.write(_CLEAR_LINE)

    def plan(self, title: str, steps: list[str]) -> None:
        """Print a compact, styled autonomous plan."""
        self.line(f"{self.accent('plan')} {title}")
        for index, step in enumerate(steps, start=1):
            self.line(f"  {self.muted(f'{index:02d}')} {step}")

    def toggle(self) -> bool:
        """Flip animation for the current session; return the new state."""
        self.enabled = not self.enabled
        self.animate = supports_animation(self.stream, self.enabled) and not os.getenv("NO_COLOR")
        self.color = self.animate
        if self.color:
            _enable_windows_ansi()
        return self.animate
