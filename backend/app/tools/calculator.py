# Module: backend.app.tools.calculator
"""
Calculator Tool for Friday AI Assistant.
Safe mathematical evaluation engine.
"""

from __future__ import annotations

import ast
import operator
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult


# Allowed operations
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _calculate(node: ast.AST) -> float:
    """Safely evaluate an AST expression."""
    if isinstance(node, ast.Expression):
        return _calculate(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numbers are allowed.")

    if isinstance(node, ast.BinOp):
        operation = _OPERATORS.get(type(node.op))
        if operation is None:
            raise ValueError("Operation not allowed.")
        left = _calculate(node.left)
        right = _calculate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("Power is too large.")
        return operation(left, right)

    if isinstance(node, ast.UnaryOp):
        operation = _OPERATORS.get(type(node.op))
        if operation is None:
            raise ValueError("Operation not allowed.")
        return operation(_calculate(node.operand))

    raise ValueError("Invalid mathematical expression.")


class CalculatorInput(BaseModel):
    expression: str = Field(..., description="The mathematical expression to evaluate (e.g., '(240 * 1.18) / 12', 'sqrt(144)', '2^16').")


class CalculatorTool(BaseTool):
    name: str = "calculate"
    description: str = "Safely computes mathematical arithmetic expressions and conversions."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    category: str = "general"
    args_schema = CalculatorInput

    def run(self, expression: str, **kwargs: Any) -> ToolResult:
        if not expression or not expression.strip():
            return ToolResult(tool_name=self.name, success=False, error="Please provide a calculation expression.")

        expr = expression.strip().replace("^", "**")
        if len(expr) > 200:
            return ToolResult(tool_name=self.name, success=False, error="Calculation expression is too long.")

        try:
            tree = ast.parse(expr, mode="eval")
            result = _calculate(tree)
            if isinstance(result, float) and result.is_integer():
                formatted = str(int(result))
            elif isinstance(result, float):
                formatted = f"{result:.10g}"
            else:
                formatted = str(result)

            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"expression": expression, "result": formatted, "numeric_value": result},
                metadata={"summary": f"{expression} = {formatted}"}
            )
        except ZeroDivisionError:
            return ToolResult(tool_name=self.name, success=False, error="Cannot divide by zero.")
        except Exception as exc:
            return ToolResult(tool_name=self.name, success=False, error=f"Invalid calculation: {str(exc)}")


def calculate(expression: str) -> str:
    """Legacy helper."""
    tool = CalculatorTool()
    res = tool.run(expression=expression)
    if res.success and res.data:
        return str(res.data.get("result"))
    return res.error or "Calculation error."