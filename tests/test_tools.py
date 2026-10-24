"""Tests for the v0.3 tool layer: registry, built-in tools, permissions, parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from dream_ai.config import Settings
from dream_ai.core import DreamAIAgent
from dream_ai.exceptions import ToolConfirmationRequired, ToolError
from dream_ai.providers import LocalEchoProvider
from dream_ai.tools import ToolRegistry, build_tool_registry, parse_tool_calls
from dream_ai.tools.builtin.calculator import CalculatorTool
from dream_ai.tools.builtin.clock import ClockTool
from dream_ai.tools.builtin.files import FileReadTool, FileWriteTool


def _settings(
    tmp_path: Path,
    *,
    tools: bool = True,
    file_access: bool = False,
    web_search: bool = False,
) -> Settings:
    return Settings(
        provider="local",
        base_url="",
        api_key="",
        model="local",
        system_prompt="You are Dream AI.",
        data_dir=tmp_path,
        persistence_enabled=False,
        tools_enabled=tools,
        file_access_enabled=file_access,
        web_search_enabled=web_search,
        workspace_dir=tmp_path / "workspace",
    )


def _agent(settings: Settings) -> DreamAIAgent:
    return DreamAIAgent(
        provider=LocalEchoProvider(),
        tools=build_tool_registry(settings),
        system_prompt="You are Dream AI.",
    )


# --- Calculator -------------------------------------------------------------


def test_calculator_evaluates_basic_expressions() -> None:
    tool = CalculatorTool()

    assert "14" in tool.run(expression="2 + 3 * 4")
    assert "4" in tool.run(expression="(12 + 8) / 5")
    assert "12" in tool.run(expression="sqrt(144)")
    assert "7" in tool.run(expression="abs(-7)")


def test_calculator_rejects_division_by_zero() -> None:
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    with pytest.raises(ToolError):
        registry.execute("calculator", expression="1 / 0")


@pytest.mark.parametrize(
    "bad",
    [
        "__import__('os')",
        "x + 1",
        "os.getcwd()",
        "[1, 2][0]",
        "open('config.py')",
    ],
)
def test_calculator_rejects_unsupported_constructs(bad: str) -> None:
    with pytest.raises(ToolError):
        CalculatorTool().run(expression=bad)


def test_calculator_requires_expression() -> None:
    with pytest.raises(ToolError):
        CalculatorTool().run(expression="")


# --- Clock ------------------------------------------------------------------


def test_clock_returns_local_time() -> None:
    result = ClockTool().run()

    assert "Current local time" in result
    assert "Weekday:" in result


# --- Sandboxed file tools ----------------------------------------------------


def test_file_write_and_read_roundtrip(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    writer = FileWriteTool(workspace)
    reader = FileReadTool(workspace)

    writer.run(path="notes/hello.txt", content="Dream AI v0.3")
    result = reader.run(path="notes/hello.txt")

    assert "Dream AI v0.3" in result


def test_file_tools_reject_traversal_and_absolute_paths(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    writer = FileWriteTool(workspace)
    reader = FileReadTool(workspace)

    with pytest.raises(ToolError):
        reader.run(path="../../etc/passwd")
    with pytest.raises(ToolError):
        writer.run(path="../escape.txt", content="x")
    with pytest.raises(ToolError):
        reader.run(path=str(tmp_path / "outside.txt"))


def test_file_read_missing_file_raises(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(ToolError):
        FileReadTool(workspace).run(path="nope.txt")


# --- Registry and permission switches ---------------------------------------


def test_factory_registers_safe_tools_by_default(tmp_path: Path) -> None:
    registry = build_tool_registry(_settings(tmp_path))

    assert registry.names() == ["calculator", "clock"]


def test_factory_file_and_web_tools_opt_in(tmp_path: Path) -> None:
    registry = build_tool_registry(_settings(tmp_path, file_access=True, web_search=True))

    assert registry.names() == ["calculator", "clock", "file_read", "file_write", "web_search"]


def test_factory_disabled_when_tools_off(tmp_path: Path) -> None:
    registry = build_tool_registry(_settings(tmp_path, tools=False))

    assert registry.names() == []


def test_registry_rejects_duplicate_and_unknown_tools() -> None:
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    with pytest.raises(ToolError):
        registry.register(CalculatorTool())
    with pytest.raises(ToolError):
        registry.execute("nope")


# --- Structured call parser -------------------------------------------------


def test_parser_extracts_tool_call() -> None:
    text = (
        'Before <<TOOL {"name": "calculator", '
        '"arguments": {"expression": "1+1"}}>> after'
    )

    calls = parse_tool_calls(text)

    assert len(calls) == 1
    assert calls[0].name == "calculator"
    assert calls[0].arguments == {"expression": "1+1"}


def test_parser_returns_empty_without_blocks() -> None:
    assert parse_tool_calls("plain reply with no tool call") == []


def test_parser_rejects_bad_json() -> None:
    with pytest.raises(ToolError):
        parse_tool_calls("<<TOOL {not json}>>")


def test_parser_rejects_non_object_arguments() -> None:
    with pytest.raises(ToolError):
        parse_tool_calls('<<TOOL {"name": "clock", "arguments": [1, 2]}>>')


# --- Agent integration -------------------------------------------------------


def test_agent_lists_safe_tools(tmp_path: Path) -> None:
    agent = _agent(_settings(tmp_path))

    assert [tool["name"] for tool in agent.list_tools()] == ["calculator", "clock"]


def test_file_write_requires_confirmation(tmp_path: Path) -> None:
    agent = _agent(_settings(tmp_path, file_access=True))

    with pytest.raises(ToolConfirmationRequired):
        agent.execute_tool("file_write", path="a.txt", content="hi")

    result = agent.execute_tool("file_write", confirmed=True, path="a.txt", content="hi")
    assert "characters" in result


def test_agent_unknown_tool_raises(tmp_path: Path) -> None:
    agent = _agent(_settings(tmp_path))

    with pytest.raises(ToolError):
        agent.execute_tool("does_not_exist")


def test_agent_runs_tool_calls_from_text(tmp_path: Path) -> None:
    agent = _agent(_settings(tmp_path))
    text = '<<TOOL {"name": "calculator", "arguments": {"expression": "2 * 3"}}>>'

    results = agent.run_tool_calls(text)

    assert len(results) == 1
    call, output = results[0]
    assert call.name == "calculator"
    assert "6" in output


def test_provider_tools_schema_shape(tmp_path: Path) -> None:
    agent = _agent(_settings(tmp_path))
    schema = agent.provider_tools_schema()

    assert schema[0]["type"] == "function"
    assert schema[0]["function"]["name"] == "calculator"
