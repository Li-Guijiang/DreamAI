"""Autonomous execution loop: think → act → observe → reflect.

The engine receives a plan (either provided explicitly or produced by a
:class:`Planner`), runs each step through the agent's tool registry, records
every phase in an explainable trace, enforces a step budget, retries failed
steps, and asks for approval before protected actions.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from ..exceptions import ToolConfirmationRequired, ToolError
from .models import (
    ExecutionResult,
    Phase,
    PlanStep,
    RunStatus,
    StepStatus,
    TraceEntry,
)
from .planner import Planner, RuleBasedPlanner

if TYPE_CHECKING:
    from ..core.agent import DreamAIAgent

ConfirmationCallback = Callable[[PlanStep, str, dict[str, Any]], bool]
EventCallback = Callable[[TraceEntry], None]


class AutonomyEngine:
    """Run an ordered plan through a think → act → observe → reflect loop."""

    def __init__(
        self,
        agent: DreamAIAgent,
        *,
        planner: Planner | None = None,
        max_steps: int = 10,
        max_retries: int = 2,
        confirmation_callback: ConfirmationCallback | None = None,
        on_event: EventCallback | None = None,
    ) -> None:
        self._agent = agent
        self._planner = planner or RuleBasedPlanner()
        self._max_steps = max(1, int(max_steps))
        self._max_retries = max(0, int(max_retries))
        self._confirm = confirmation_callback
        self._on_event = on_event
        self._trace: list[TraceEntry] = []

    # -- Public API ---------------------------------------------------------

    def run(
        self, objective: str, plan: list[PlanStep] | None = None
    ) -> ExecutionResult:
        """Execute ``objective`` and return an explainable :class:`ExecutionResult`."""
        self._trace = []
        steps = list(plan or self._planner.decompose(objective))

        self._log(None, Phase.PLAN, f"Built a plan with {len(steps)} step(s).")
        for index, step in enumerate(steps):
            target = f" [{step.tool}]" if step.tool else " [conversation]"
            self._log(index, Phase.PLAN, f"Step {index + 1}: {step.title}{target}")

        act_budget = self._max_steps
        final_status = RunStatus.COMPLETED

        for index, step in enumerate(steps):
            if act_budget <= 0:
                self._log(
                    None,
                    Phase.ABORT,
                    f"Step budget of {self._max_steps} act(s) exhausted.",
                )
                final_status = RunStatus.BUDGET_EXHAUSTED
                break

            step.status = StepStatus.RUNNING
            self._log(index, Phase.THINK, f"Start step: {step.title}")

            if step.tool is None:
                step.status = StepStatus.SUCCEEDED
                step.observation = "Handled directly in conversation; no tool was required."
                self._log(index, Phase.OBSERVE, step.observation)
                step.reflection = "No capability was required; move on to the next step."
                self._log(index, Phase.REFLECT, step.reflection)
                continue

            schema = self._tool_schema(step.tool)
            protected = bool(schema and schema.get("requires_confirmation")) or step.needs_confirmation

            if protected:
                self._log(
                    index,
                    Phase.CONFIRM,
                    f"Protected action '{step.tool}' needs approval.",
                    tool_name=step.tool,
                    arguments=step.arguments,
                )
                if not self._approved(step):
                    step.status = StepStatus.SKIPPED
                    step.error = "User declined the protected action."
                    self._log(
                        index,
                        Phase.ABORT,
                        "User declined a protected action; run cancelled.",
                        tool_name=step.tool,
                    )
                    final_status = RunStatus.CANCELLED
                    break

            success = False
            last_error = ""
            while step.attempts <= self._max_retries:
                if act_budget <= 0:
                    final_status = RunStatus.BUDGET_EXHAUSTED
                    break

                step.attempts += 1
                act_budget -= 1
                self._log(
                    index,
                    Phase.ACT,
                    f"Call '{step.tool}' (attempt {step.attempts}).",
                    tool_name=step.tool,
                    arguments=step.arguments,
                )

                try:
                    output = self._agent.execute_tool(
                        step.tool, confirmed=True, **step.arguments
                    )
                    step.observation = output
                    success = True
                    break
                except ToolConfirmationRequired as exc:
                    last_error = str(exc)
                    step.status = StepStatus.SKIPPED
                    step.error = last_error
                    self._log(
                        index,
                        Phase.ABORT,
                        f"Action '{step.tool}' was not approved: {last_error}",
                        tool_name=step.tool,
                    )
                    final_status = RunStatus.CANCELLED
                    break
                except ToolError as exc:
                    last_error = str(exc)
                    self._log(
                        index,
                        Phase.REFLECT,
                        f"Attempt {step.attempts} failed: {last_error}",
                    )
                    if act_budget <= 0:
                        final_status = RunStatus.BUDGET_EXHAUSTED
                        break
                    # The while condition stops retrying once retries are spent.

            if final_status is RunStatus.CANCELLED:
                break

            if success:
                step.status = StepStatus.SUCCEEDED
                self._log(index, Phase.OBSERVE, step.observation)
                step.reflection = "Step completed successfully; observation recorded."
                self._log(index, Phase.REFLECT, step.reflection)
            else:
                step.status = StepStatus.FAILED
                step.error = last_error
                self._log(
                    index,
                    Phase.ABORT,
                    f"Step failed after {step.attempts} attempt(s): {last_error}",
                )
                if final_status is not RunStatus.BUDGET_EXHAUSTED:
                    final_status = RunStatus.FAILED
                break

        return self._finalize(objective, steps, final_status)

    # -- Internals ----------------------------------------------------------

    def _tool_schema(self, name: str) -> dict[str, Any] | None:
        for schema in self._agent.list_tools():
            if schema.get("name") == name:
                return schema
        return None

    def _approved(self, step: PlanStep) -> bool:
        if self._confirm is None:
            # Safe default: a protected action without a callback is declined.
            return False
        return bool(self._confirm(step, step.tool or "", dict(step.arguments)))

    def _log(
        self,
        step_index: int | None,
        phase: Phase,
        content: str,
        *,
        tool_name: str | None = None,
        arguments: dict[str, Any] | None = None,
    ) -> None:
        entry = TraceEntry(
            step_index=step_index,
            phase=phase,
            content=content,
            tool_name=tool_name,
            arguments=arguments,
        )
        self._trace.append(entry)
        if self._on_event is not None:
            self._on_event(entry)

    def _finalize(
        self,
        objective: str,
        steps: list[PlanStep],
        status: RunStatus,
    ) -> ExecutionResult:
        summary = self._summarize(objective, steps, status)
        phase = Phase.DONE if status is RunStatus.COMPLETED else Phase.ABORT
        self._log(None, phase, summary)
        return ExecutionResult(
            objective=objective,
            status=status,
            steps=steps,
            trace=list(self._trace),
            final_summary=summary,
            total_steps=len(steps),
        )

    @staticmethod
    def _summarize(
        objective: str,
        steps: list[PlanStep],
        status: RunStatus,
    ) -> str:
        succeeded = sum(step.status is StepStatus.SUCCEEDED for step in steps)
        lines = [
            f"Objective: {objective}",
            f"Status: {status.value}",
            f"Steps completed: {succeeded}/{len(steps)}",
        ]
        for index, step in enumerate(steps, start=1):
            detail = step.observation if step.observation else step.error
            suffix = f" → {detail}" if detail else ""
            lines.append(f"  {index}. [{step.status.value}] {step.title}{suffix}")
        return "\n".join(lines)
