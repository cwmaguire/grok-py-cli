"""Example calculator tool to demonstrate the tool framework."""

import logging
from typing import Union

from grok_py.tools.base import AsyncTool, ToolCategory, ToolResult, register_tool


class CalculatorTool(AsyncTool):
    """A simple calculator tool for basic arithmetic operations."""

    def __init__(self):
        """Initialize the calculator tool."""
        super().__init__(
            name="calculator",
            description="Perform basic arithmetic calculations including addition, subtraction, multiplication, and division",
            category=ToolCategory.UTILITY
        )

    async def execute(
        self,
        operation: str,
        a: Union[int, float],
        b: Union[int, float]
    ) -> ToolResult:
        """Execute a calculator operation.

        Args:
            operation: The operation to perform (add, subtract, multiply, divide)
            a: First number
            b: Second number

        Returns:
            ToolResult with calculation result
        """
        try:
            # Validate inputs
            if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
                return ToolResult(
                    success=False,
                    error="Both 'a' and 'b' must be numbers",
                    data={"operation": operation, "a": a, "b": b}
                )

            # Perform calculation
            if operation == "add":
                result = a + b
                description = f"{a} + {b} = {result}"
            elif operation == "subtract":
                result = a - b
                description = f"{a} - {b} = {result}"
            elif operation == "multiply":
                result = a * b
                description = f"{a} × {b} = {result}"
            elif operation == "divide":
                if b == 0:
                    return ToolResult(
                        success=False,
                        error="Division by zero is not allowed",
                        data={"operation": operation, "a": a, "b": b}
                    )
                result = a / b
                description = f"{a} ÷ {b} = {result}"
            else:
                return ToolResult(
                    success=False,
                    error=f"Unsupported operation: {operation}. Supported: add, subtract, multiply, divide",
                    data={"operation": operation, "a": a, "b": b}
                )

            return ToolResult(
                success=True,
                data={
                    "result": result,
                    "operation": operation,
                    "a": a,
                    "b": b,
                    "description": description
                },
                metadata={
                    "calculation_type": "basic_arithmetic",
                    "precision": "exact"
                }
            )

        except Exception as e:
            self.logger.error(f"Calculator error: {e}")
            return ToolResult(
                success=False,
                error=f"Calculation failed: {str(e)}",
                data={"operation": operation, "a": a, "b": b}
            )