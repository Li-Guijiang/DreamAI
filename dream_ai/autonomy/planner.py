"""Plan decomposition for the autonomous layer.

The v0.4 baseline ships a deterministic :class:`RuleBasedPlanner` so the
reasoning loop is testable offline and in demos without a hosted model. A
future LLM-backed planner can implement the same interface and emit richer,
multi-step plans.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from .models import PlanStep

_TIME_KEYWORDS = (
    "time",
    "date",
    "today",
    "clock",
    "now",
    "weekday",
    "几点",
    "时间",
    "日期",
    "星期",
)

_CALC_KEYWORDS = (
    "calculate",
    "compute",
    "sum",
    "add",
    "multiply",
    "percent",
    "sqrt",
    "average",
    "how much",
    "几",
    "多少",
    "计算",
    "求和",
)

_EXPRESSION_PATTERN = re.compile(
    r"[A-Za-z]*(?:[0-9]|\()[0-9A-Za-z+\-*/().%\s]*(?:[0-9)]|\()"
)
_QUOTED_EXPRESSION = re.compile(r'"([^"]*[0-9][^"]*)"')


class Planner(ABC):
    """Turn an objective into an ordered list of plan steps."""

    @abstractmethod
    def decompose(self, objective: str) -> list[PlanStep]:
        """Return the ordered plan for ``objective``."""


class RuleBasedPlanner(Planner):
    """Keyword-driven offline planner mapping intent to safe built-in tools.

    It only emits a tool step when a concrete argument can be resolved
    deterministically; otherwise the request falls back to a conversation
    step so the engine still runs through the full loop.
    """

    def decompose(self, objective: str) -> list[PlanStep]:
        text = objective.lower()
        steps: list[PlanStep] = []

        if any(keyword in text for keyword in _TIME_KEYWORDS):
            steps.append(
                PlanStep(
                    title="Read the current local time and date.",
                    tool="clock",
                    arguments={},
                )
            )

        if any(keyword in text for keyword in _CALC_KEYWORDS):
            expression = self._extract_expression(objective)
            if expression:
                steps.append(
                    PlanStep(
                        title=f"Evaluate the arithmetic: {expression}",
                        tool="calculator",
                        arguments={"expression": expression},
                    )
                )

        if not steps:
            steps.append(
                PlanStep(
                    title="Answer the request directly in conversation.",
                    tool=None,
                    arguments={},
                )
            )

        return steps

    @staticmethod
    def _extract_expression(objective: str) -> str | None:
        """Pull a concrete arithmetic expression out of the objective.

        A quoted expression wins; otherwise a bare arithmetic token sequence
        is matched. Returns ``None`` when nothing concrete was found, so the
        planner does not emit a calculator step with missing arguments.
        """
        quoted = _QUOTED_EXPRESSION.search(objective)
        if quoted:
            return quoted.group(1).strip()

        match = _EXPRESSION_PATTERN.search(objective)
        if match and re.search(r"[0-9]", match.group(0)):
            return match.group(0).strip()
        return None
