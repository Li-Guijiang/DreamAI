"""Tests for the v0.4 autonomous planning layer.

Covers rule-based decomposition, the think → act → observe → reflect loop,
step budget, retry policy, the confirmation gate, and conversation memory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dream_ai.autonomy import (
    PlanStep,
    RuleBasedPlanner,
    RunStatus,
    StepStatus,
)
from dream_ai.config import Settings, load_settings
from dream_ai.core import DreamAIAgent
from dream_ai.exceptions import ConfigurationError, ToolError
from dream_ai.providers import LocalEchoProvider
from dream_ai.tools import build_tool_registry
from dream_ai.tools.base import Tool

# --- Test doubles ------------------------------------------------------------


class FlakyTool(Tool):
    """A tool that fails ``fail_times`` times before succeeding."""

    def __init__(self, fail_times: int = 0, result: str = "flaky result") -> None:
        self._fail_times = fail_times
        self._calls = 0
        self._result = result

    @property
    def name(self) -> str:
        return "flaky"

    @property
    def description(self) -> str:
        return "Test tool that fails a configurable number of times."

    @property
    def risk(self) -> str:
        return "safe"

    @property
    def attempts(self) -> int:
        return self._calls

    def run(self, **kwargs: Any) -> str:
        self._calls += 1
        if self._calls <= self._fail_times:
            raise ToolError("boom")
        return self._result


class ConfirmTool(Tool):
    """A protected tool that requires explicit confirmation before running."""

    @property
    def name(self) -> str:
        return "confirm_tool"

    @property
    def description(self) -> str:
        return "Protected test tool."

    @property
    def risk(self) -> str:
        return "protected"

    @property
    def requires_confirmation(self) -> bool:
        return True

    def run(self, **kwargs: Any) -> str:
        return "protected action completed"


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    base: dict[str, Any] = dict(
        provider="local",
        base_url="",
        api_key="",
        model="local",
        system_prompt="You are Dream AI.",
        data_dir=tmp_path,
        persistence_enabled=False,
        tools_enabled=True,
        file_access_enabled=False,
        web_search_enabled=False,
        workspace_dir=tmp_path / "workspace",
    )
    base.update(overrides)
    return Settings(**base)


def _agent(settings: Settings, *extra: Tool) -> DreamAIAgent:
    agent = DreamAIAgent(
        provider=LocalEchoProvider(),
        tools=build_tool_registry(settings),
        system_prompt="You are Dream AI.",
    )
    for tool in extra:
        agent.tools.register(tool)
    return agent


# --- Settings defaults and parsing -------------------------------------------


def test_settings_autonomy_defaults(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    assert settings.autonomy_enabled is True
    assert settings.max_steps == 10
    assert settings.max_retries == 2
    assert settings.autonomy_verbose is False


def test_settings_parses_autonomy_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DREAMAI_AUTONOMY_ENABLED", "false")
    monkeypatch.setenv("DREAMAI_MAX_STEPS", "3")
    monkeypatch.setenv("DREAMAI_MAX_RETRIES", "1")
    monkeypatch.setenv("DREAMAI_AUTONOMY_VERBOSE", "true")

    settings = load_settings()

    assert settings.autonomy_enabled is False
    assert settings.max_steps == 3
    assert settings.max_retries == 1
    assert settings.autonomy_verbose is True


def test_settings_invalid_budget_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DREAMAI_MAX_STEPS", "abc")
    monkeypatch.setenv("DREAMAI_MAX_RETRIES", "-3")

    settings = load_settings()

    assert settings.max_steps == 10
    assert settings.max_retries == 2


# --- Rule-based planner ------------------------------------------------------


def test_planner_maps_time_intent_to_clock() -> None:
    steps = RuleBasedPlanner().decompose("What time is it now?")

    assert len(steps) == 1
    assert steps[0].tool == "clock"


def test_planner_maps_calculation_intent_to_calculator() -> None:
    steps = RuleBasedPlanner().decompose("calculate 12 * 7")

    calc = next(step for step in steps if step.tool == "calculator")
    expression = calc.arguments["expression"]
    assert "12" in expression
    assert "*" in expression


def test_planner_prefers_quoted_expression() -> None:
    steps = RuleBasedPlanner().decompose('What is "sqrt(144)"?')

    calc = next(step for step in steps if step.tool == "calculator")
    assert calc.arguments["expression"] == "sqrt(144)"


def test_planner_falls_back_to_conversation_step() -> None:
    steps = RuleBasedPlanner().decompose("Tell me about dreams")

    assert len(steps) == 1
    assert steps[0].tool is None


def test_planner_builds_two_step_mixed_plan() -> None:
    steps = RuleBasedPlanner().decompose("What time is it now, and calculate 12 * 7?")

    assert [step.tool for step in steps] == ["clock", "calculator"]


# --- Engine: successful multi-step run ---------------------------------------


def test_engine_completes_safe_multi_step_plan(tmp_path: Path) -> None:
    agent = _agent(_settings(tmp_path))
    plan = [
        PlanStep(title="Read the time.", tool="clock", arguments={}),
        PlanStep(title="Evaluate.", tool="calculator", arguments={"expression": "2 + 3"}),
    ]

    result = agent.autonomous_task("Check the time and compute 2 + 3.", plan=plan)

    assert result.status is RunStatus.COMPLETED
    assert [step.status for step in result.steps] == [
        StepStatus.SUCCEEDED,
        StepStatus.SUCCEEDED,
    ]

    phases = {entry.phase for entry in result.trace}
    assert {"plan", "think", "act", "observe", "reflect"} <= phases
    assert "2 + 3" in result.steps[1].observation


def test_result_is_serializable(tmp_path: Path) -> None:
    agent = _agent(_settings(tmp_path))
    result = agent.autonomous_task("What time is it now?")

    payload = result.to_dict()

    assert payload["objective"] == "What time is it now?"
    assert payload["status"] == "completed"
    assert len(payload["steps"]) == 1
    assert payload["trace"]


# --- Budget ------------------------------------------------------------------


def test_engine_stops_when_step_budget_exhausted(tmp_path: Path) -> None:
    agent = _agent(_settings(tmp_path))
    plan = [
        PlanStep(title="First clock.", tool="clock", arguments={}),
        PlanStep(title="Second clock.", tool="clock", arguments={}),
    ]

    result = agent.autonomous_task(
        "Two clock calls.", plan=plan, max_steps=1
    )

    assert result.status is RunStatus.BUDGET_EXHAUSTED
    assert result.steps[0].status is StepStatus.SUCCEEDED
    assert result.steps[1].status is StepStatus.PENDING
    assert any(entry.phase == "abort" for entry in result.trace)


def test_conversation_steps_do_not_consume_act_budget(tmp_path: Path) -> None:
    agent = _agent(_settings(tmp_path))
    plan = [
        PlanStep(title="Talk first.", tool=None),
        PlanStep(title="Talk second.", tool=None),
    ]

    result = agent.autonomous_task("Talk twice.", plan=plan, max_steps=1)

    assert result.status is RunStatus.COMPLETED
    assert all(step.status is StepStatus.SUCCEEDED for step in result.steps)


# --- Retry policy ------------------------------------------------------------


def test_engine_retries_until_success(tmp_path: Path) -> None:
    tool = FlakyTool(fail_times=2)
    agent = _agent(_settings(tmp_path), tool)
    plan = [PlanStep(title="Flaky.", tool="flaky", arguments={})]

    result = agent.autonomous_task("Retry a flaky tool.", plan=plan, max_retries=2)

    assert result.status is RunStatus.COMPLETED
    assert result.steps[0].status is StepStatus.SUCCEEDED
    assert tool.attempts == 3
    assert result.steps[0].attempts == 3


def test_engine_fails_after_retries_are_spent(tmp_path: Path) -> None:
    tool = FlakyTool(fail_times=3)
    agent = _agent(_settings(tmp_path), tool)
    plan = [PlanStep(title="Flaky.", tool="flaky", arguments={})]

    result = agent.autonomous_task("Retries exhausted.", plan=plan, max_retries=1)

    assert result.status is RunStatus.FAILED
    assert result.steps[0].status is StepStatus.FAILED
    assert result.steps[0].error
    assert tool.attempts == 2


# --- Confirmation gate -------------------------------------------------------


def test_protected_action_declined_cancels_the_run(tmp_path: Path) -> None:
    agent = _agent(_settings(tmp_path), ConfirmTool())
    plan = [PlanStep(title="Write a file.", tool="confirm_tool", arguments={})]

    result = agent.autonomous_task(
        "Write a file.", plan=plan, confirmation_callback=lambda *_: False
    )

    assert result.status is RunStatus.CANCELLED
    assert result.steps[0].status is StepStatus.SKIPPED


def test_protected_action_approved_runs(tmp_path: Path) -> None:
    agent = _agent(_settings(tmp_path), ConfirmTool())
    plan = [PlanStep(title="Write a file.", tool="confirm_tool", arguments={})]

    result = agent.autonomous_task(
        "Write a file.", plan=plan, confirmation_callback=lambda *_: True
    )

    assert result.status is RunStatus.COMPLETED
    assert result.steps[0].status is StepStatus.SUCCEEDED
    assert "completed" in result.steps[0].observation


def test_protected_action_without_callback_is_declined(tmp_path: Path) -> None:
    agent = _agent(_settings(tmp_path), ConfirmTool())
    plan = [PlanStep(title="Write a file.", tool="confirm_tool", arguments={})]

    result = agent.autonomous_task("Write a file.", plan=plan)

    assert result.status is RunStatus.CANCELLED


# --- Failure paths ------------------------------------------------------------


def test_unknown_tool_marks_step_failed(tmp_path: Path) -> None:
    agent = _agent(_settings(tmp_path))
    plan = [PlanStep(title="Ghost.", tool="ghost", arguments={})]

    result = agent.autonomous_task("Call a missing tool.", plan=plan, max_retries=0)

    assert result.status is RunStatus.FAILED
    assert result.steps[0].status is StepStatus.FAILED


# --- Agent integration and memory --------------------------------------------


def test_autonomous_task_records_objective_and_summary(tmp_path: Path) -> None:
    agent = _agent(_settings(tmp_path))

    result = agent.autonomous_task("What time is it now?")

    assert result.succeeded is True
    roles = [message["role"] for message in agent.history]
    assert "user" in roles
    assert "assistant" in roles
    assert agent.history[-1]["content"] == result.final_summary
    assert agent.last_execution is result


def test_disabled_autonomy_raises_configuration_error(tmp_path: Path) -> None:
    agent = DreamAIAgent(
        provider=LocalEchoProvider(),
        tools=build_tool_registry(_settings(tmp_path)),
        autonomy_enabled=False,
    )

    with pytest.raises(ConfigurationError):
        agent.autonomous_task("Anything")
