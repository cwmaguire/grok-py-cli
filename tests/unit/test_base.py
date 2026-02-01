"""Unit tests for base tool classes and models."""

import inspect
import pytest
from pydantic import ValidationError

from grok_py.tools.base import (
    ToolCategory,
    ToolResult,
    ToolParameter,
    ToolDefinition,
    BaseTool,
    AsyncTool,
    SyncTool,
)


class TestToolResult:
    """Test suite for ToolResult model."""

    def test_successful_result(self):
        """Test creating a successful tool result."""
        result = ToolResult(
            success=True,
            data={"key": "value"},
            metadata={"type": "test"}
        )

        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.metadata == {"type": "test"}

    def test_failed_result(self):
        """Test creating a failed tool result."""
        result = ToolResult(
            success=False,
            error="Something went wrong",
            data={"attempted": "operation"}
        )

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data == {"attempted": "operation"}
        assert result.metadata == {}

    def test_result_with_defaults(self):
        """Test ToolResult with default values."""
        result = ToolResult(success=True)

        assert result.success is True
        assert result.data is None
        assert result.error is None
        assert result.metadata == {}


class TestToolParameter:
    """Test suite for ToolParameter model."""

    def test_basic_parameter(self):
        """Test creating a basic tool parameter."""
        param = ToolParameter(
            name="test_param",
            type="string",
            description="A test parameter"
        )

        assert param.name == "test_param"
        assert param.type == "string"
        assert param.description == "A test parameter"
        assert param.required is False
        assert param.default is None
        assert param.enum is None

    def test_required_parameter(self):
        """Test creating a required parameter."""
        param = ToolParameter(
            name="required_param",
            type="int",
            description="Required parameter",
            required=True
        )

        assert param.required is True


class TestToolDefinition:
    """Test suite for ToolDefinition model."""

    def test_basic_definition(self):
        """Test creating a basic tool definition."""
        definition = ToolDefinition(
            name="test_tool",
            description="A test tool",
            category=ToolCategory.UTILITY
        )

        assert definition.name == "test_tool"
        assert definition.description == "A test tool"
        assert definition.category == ToolCategory.UTILITY
        assert definition.parameters == {}
        assert definition.examples == []
        assert definition.version == "1.0.0"


class MockBaseTool(BaseTool):
    """Mock implementation of BaseTool for testing."""

    def __init__(self, name="mock_tool", description="Mock tool", category=ToolCategory.UTILITY):
        super().__init__(name, description, category)

    async def execute(self, **kwargs):
        return ToolResult(success=True, data={"executed": True})


class TestBaseTool:
    """Test suite for BaseTool class."""

    def test_initialization(self):
        """Test BaseTool initialization."""
        tool = MockBaseTool("test_tool", "Test tool", ToolCategory.DEVELOPMENT)

        assert tool.name == "test_tool"
        assert tool.description == "Test tool"
        assert tool.category == ToolCategory.DEVELOPMENT
        assert hasattr(tool, 'logger')

    def test_get_definition(self):
        """Test tool definition generation."""
        tool = MockBaseTool("test_tool", "Test tool", ToolCategory.UTILITY)
        definition = tool.get_definition()

        assert isinstance(definition, ToolDefinition)
        assert definition.name == "test_tool"
        assert definition.description == "Test tool"
        assert definition.category == ToolCategory.UTILITY

    def test_validate_parameters_valid(self):
        """Test parameter validation with valid parameters."""
        tool = MockBaseTool()
        # Mock execute method with parameters
        tool.execute = lambda **kwargs: ToolResult(success=True)
        sig = inspect.signature(lambda self, param1: None)
        tool._get_param_type = lambda p: "string"

        # This would normally be tested with a real method signature
        # For now, test the basic validation logic
        validated = tool.validate_parameters()
        assert validated == {}

    def test_validate_parameters_missing_required(self):
        """Test parameter validation with missing required parameter."""
        tool = MockBaseTool()

        # Mock a definition with required parameter
        tool.get_definition = lambda: ToolDefinition(
            name="test",
            description="test",
            category=ToolCategory.UTILITY,
            parameters={
                "required_param": ToolParameter(
                    name="required_param",
                    type="string",
                    description="Required",
                    required=True
                )
            }
        )

        with pytest.raises(ValueError, match="Required parameter 'required_param' is missing"):
            tool.validate_parameters()


class TestAsyncTool:
    """Test suite for AsyncTool class."""

    def test_async_tool_inheritance(self):
        """Test that AsyncTool inherits from BaseTool."""
        class TestAsyncToolSubclass(AsyncTool):
            async def execute(self, **kwargs):
                return ToolResult(success=True)

        tool = TestAsyncToolSubclass("async_tool", "Async tool", ToolCategory.UTILITY)
        assert isinstance(tool, BaseTool)
        assert tool.name == "async_tool"

    def test_async_tool_execute_method(self):
        """Test that AsyncTool has execute method."""
        class TestAsyncToolSubclass(AsyncTool):
            async def execute(self, **kwargs):
                return ToolResult(success=True)

        tool = TestAsyncToolSubclass("async_tool", "Async tool", ToolCategory.UTILITY)
        assert hasattr(tool, 'execute')
        assert inspect.iscoroutinefunction(tool.execute)


class TestSyncTool:
    """Test suite for SyncTool class."""

    def test_sync_tool_inheritance(self):
        """Test that SyncTool inherits from BaseTool."""
        class TestSyncToolSubclass(SyncTool):
            def execute_sync(self, **kwargs):
                return ToolResult(success=True)

        tool = TestSyncToolSubclass("sync_tool", "Sync tool", ToolCategory.UTILITY)
        assert isinstance(tool, BaseTool)
        assert tool.name == "sync_tool"

    def test_sync_tool_methods(self):
        """Test that SyncTool has required methods."""
        class TestSyncToolSubclass(SyncTool):
            def execute_sync(self, **kwargs):
                return ToolResult(success=True)

        tool = TestSyncToolSubclass("sync_tool", "Sync tool", ToolCategory.UTILITY)
        assert hasattr(tool, 'execute')
        assert hasattr(tool, 'execute_sync')
        assert inspect.iscoroutinefunction(tool.execute)


class TestToolCategory:
    """Test suite for ToolCategory enum."""

    def test_categories_exist(self):
        """Test that all expected categories exist."""
        assert ToolCategory.FILE_OPERATION == "file_operation"
        assert ToolCategory.SYSTEM == "system"
        assert ToolCategory.DEVELOPMENT == "development"
        assert ToolCategory.NETWORK == "network"
        assert ToolCategory.UTILITY == "utility"
        assert ToolCategory.WEB == "web"