"""Safe arithmetic calculator tool.

The expression is parsed with ``ast`` and evaluated by walking an allowlist of
nodes. It never calls ``eval`` and rejects names, attributes, imports,
subscripts, comparisons, and any other unsupported Python construct.
"""

from __future__ import annotations

import ast
import math
import operator
from typing import Any

from ...exceptions import ToolError
from ..base import Tool

_ALLOWED_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.FloorDiv: operator.floordiv,
}

_ALLOWED_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_ALLOWED_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
}


class CalculatorTool(Tool):
    """Evaluate a numeric arithmetic expression."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return (
            "Evaluate a safe arithmetic expression using numbers, + - * / % // **, "
            "parentheses, and the functions abs, round, min, max, sqrt."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The arithmetic expression to evaluate.",
                }
            },
            "required": ["expression"],
        }

    def run(self, expression: str | None = None, **kwargs: Any) -> str:
        text = (expression or "").strip()
        if not text:
            raise ToolError("calculator requires a non-empty 'expression' argument.")

        value = self._evaluate(text)
        return f"{text} = {self._format(value)}"

    def _evaluate(self, expression: str) -> float:
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise ToolError(f"Invalid arithmetic expression: {expression!r}") from exc
        return self._visit(tree.body)  # type: ignore[no-any-return]

    def _visit(self, node: ast.AST) -> float:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ToolError("Only numeric constants are allowed.")

        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BIN_OPS:
            left = self._visit(node.left)
            right = self._visit(node.right)
            return _ALLOWED_BIN_OPS[type(node.op)](left, right)

        if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY_OPS:
            return _ALLOWED_UNARY_OPS[type(node.op)](self._visit(node.operand))

        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _ALLOWED_FUNCTIONS
        ):
            if node.keywords:
                raise ToolError("Keyword arguments are not supported by the calculator.")
            args = [self._visit(arg) for arg in node.args]
            return _ALLOWED_FUNCTIONS[node.func.id](*args)

        raise ToolError(f"Unsupported expression element: {type(node).__name__}")

    @staticmethod
    def _format(value: float) -> str:
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(round(value, 10))
