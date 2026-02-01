"""Unit tests for the CalculatorTool."""

import pytest

from grok_py.tools.example_calculator import CalculatorTool


class TestCalculatorTool:
    """Test suite for CalculatorTool."""

    @pytest.fixture
    def calculator(self):
        """Fixture to create a CalculatorTool instance."""
        return CalculatorTool()

    @pytest.mark.asyncio
    async def test_add_operation(self, calculator):
        """Test addition operation with valid inputs."""
        result = await calculator.execute(operation="add", a=5, b=3)

        assert result.success is True
        assert result.data["result"] == 8
        assert result.data["operation"] == "add"
        assert result.data["a"] == 5
        assert result.data["b"] == 3
        assert result.data["description"] == "5 + 3 = 8"
        assert result.metadata["calculation_type"] == "basic_arithmetic"

    @pytest.mark.asyncio
    async def test_subtract_operation(self, calculator):
        """Test subtraction operation with valid inputs."""
        result = await calculator.execute(operation="subtract", a=10, b=4)

        assert result.success is True
        assert result.data["result"] == 6
        assert result.data["operation"] == "subtract"
        assert result.data["a"] == 10
        assert result.data["b"] == 4
        assert result.data["description"] == "10 - 4 = 6"

    @pytest.mark.asyncio
    async def test_multiply_operation(self, calculator):
        """Test multiplication operation with valid inputs."""
        result = await calculator.execute(operation="multiply", a=6, b=7)

        assert result.success is True
        assert result.data["result"] == 42
        assert result.data["operation"] == "multiply"
        assert result.data["a"] == 6
        assert result.data["b"] == 7
        assert result.data["description"] == "6 × 7 = 42"

    @pytest.mark.asyncio
    async def test_divide_operation(self, calculator):
        """Test division operation with valid inputs."""
        result = await calculator.execute(operation="divide", a=15, b=3)

        assert result.success is True
        assert result.data["result"] == 5.0
        assert result.data["operation"] == "divide"
        assert result.data["a"] == 15
        assert result.data["b"] == 3
        assert result.data["description"] == "15 ÷ 3 = 5.0"

    @pytest.mark.asyncio
    async def test_divide_by_zero(self, calculator):
        """Test division by zero error."""
        result = await calculator.execute(operation="divide", a=10, b=0)

        assert result.success is False
        assert "Division by zero" in result.error
        assert result.data["operation"] == "divide"
        assert result.data["a"] == 10
        assert result.data["b"] == 0

    @pytest.mark.asyncio
    async def test_invalid_operation(self, calculator):
        """Test invalid operation error."""
        result = await calculator.execute(operation="modulo", a=10, b=3)

        assert result.success is False
        assert "Unsupported operation" in result.error
        assert result.data["operation"] == "modulo"
        assert result.data["a"] == 10
        assert result.data["b"] == 3

    @pytest.mark.asyncio
    async def test_non_numeric_inputs(self, calculator):
        """Test non-numeric inputs error."""
        result = await calculator.execute(operation="add", a="five", b=3)

        assert result.success is False
        assert "must be numbers" in result.error
        assert result.data["operation"] == "add"
        assert result.data["a"] == "five"
        assert result.data["b"] == 3