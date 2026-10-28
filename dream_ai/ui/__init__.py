"""Terminal presentation helpers for Dream AI.

The UI layer is deliberately optional and dependency-free: imports from here
must never change agent behaviour, and every effect degrades to plain text when
the output is redirected, `NO_COLOR` is set, or animations are disabled.
"""

from .motion import BANNER, Console, MotionSettings, prepare_output, supports_animation

__all__ = ["BANNER", "Console", "MotionSettings", "prepare_output", "supports_animation"]
