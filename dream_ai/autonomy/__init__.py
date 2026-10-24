"""Autonomous planning layer for Dream AI (v0.4).

Provides a planner, a think → act → observe → reflect execution engine, and
the data models that make every autonomous action explainable.
"""

from .engine import AutonomyEngine, ConfirmationCallback, EventCallback
from .models import (
    ExecutionResult,
    Phase,
    PlanStep,
    RunStatus,
    StepStatus,
    TraceEntry,
)
from .planner import Planner, RuleBasedPlanner

__all__ = [
    "AutonomyEngine",
    "ConfirmationCallback",
    "EventCallback",
    "ExecutionResult",
    "Phase",
    "PlanStep",
    "Planner",
    "RuleBasedPlanner",
    "RunStatus",
    "StepStatus",
    "TraceEntry",
]
