"""Data models for the v0.4 autonomous planning layer.

The engine records every think/act/observe/reflect phase in an explainable
trace so a multi-step run can be reviewed after the fact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class StepStatus(StrEnum):
    """Lifecycle of a single plan step."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class Phase(StrEnum):
    """A phase recorded in the execution trace."""

    PLAN = "plan"
    THINK = "think"
    ACT = "act"
    OBSERVE = "observe"
    REFLECT = "reflect"
    CONFIRM = "confirm"
    DONE = "done"
    ABORT = "abort"


class RunStatus(StrEnum):
    """Outcome of a whole autonomous run."""

    COMPLETED = "completed"
    BUDGET_EXHAUSTED = "budget_exhausted"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PlanStep:
    """One ordered action inside a plan.

    ``tool`` is ``None`` for a pure conversation step that needs no capability.
    """

    title: str
    tool: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    needs_confirmation: bool = False
    status: StepStatus = StepStatus.PENDING
    observation: str = ""
    error: str = ""
    attempts: int = 0
    reflection: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize the step for reports, logs, and the CLI trace view."""
        return {
            "title": self.title,
            "tool": self.tool,
            "arguments": dict(self.arguments),
            "needs_confirmation": self.needs_confirmation,
            "status": self.status.value,
            "observation": self.observation,
            "error": self.error,
            "attempts": self.attempts,
            "reflection": self.reflection,
        }


@dataclass
class TraceEntry:
    """A single explainable event recorded during an autonomous run."""

    step_index: int | None
    phase: Phase
    content: str
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the trace entry."""
        return {
            "step": self.step_index,
            "phase": self.phase.value,
            "content": self.content,
            "tool": self.tool_name,
            "arguments": dict(self.arguments) if self.arguments else None,
        }


@dataclass
class ExecutionResult:
    """The final outcome of an autonomous run, including plan and trace."""

    objective: str
    status: RunStatus
    steps: list[PlanStep]
    trace: list[TraceEntry]
    final_summary: str
    total_steps: int

    @property
    def succeeded(self) -> bool:
        """True when every step completed successfully."""
        return self.status is RunStatus.COMPLETED

    @property
    def succeeded_steps(self) -> list[PlanStep]:
        """Steps that finished successfully."""
        return [step for step in self.steps if step.status is StepStatus.SUCCEEDED]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the whole result for reports and logs."""
        return {
            "objective": self.objective,
            "status": self.status.value,
            "total_steps": self.total_steps,
            "final_summary": self.final_summary,
            "steps": [step.to_dict() for step in self.steps],
            "trace": [entry.to_dict() for entry in self.trace],
        }
