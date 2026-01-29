"""Base classes and interfaces for Grok CLI tools."""

import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type, Union
from enum import Enum

from pydantic import BaseModel, Field, ValidationError, validate_call


logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """Categories of tools available in the system."""
    FILE_OPERATION = "file_operation"
    SYSTEM = "system"
    DEVELOPMENT = "development"
    NETWORK = "network"
    UTILITY = "utility"
    WEB = "web"


class ToolResult(BaseModel):
    """Result returned by tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolParameter(BaseModel):
    """Definition of a tool parameter."""
    name: str
    type: str
    description: str
    required: bool = False
    default: Any = None
    enum: Optional[List[str]] = None


class ToolDefinition(BaseModel):
    """Definition of a tool for API consumption."""
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, ToolParameter] = Field(default_factory=dict)
    examples: List[str] = Field(default_factory=list)
    version: str = "1.0.0"
    author: Optional[str] = None


class BaseTool(ABC):
    """Abstract base class for all tools."""

    def __init__(self, name: str, description: str, category: ToolCategory):
        self.name = name
        self.description = description
        self.category = category
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters.

        Args:
            **kwargs: Tool parameters

        Returns:
            ToolResult: Execution result
        """
        pass

    def get_definition(self) -> ToolDefinition:
        """Get the tool definition for API consumption."""
        # Extract parameters from the execute method signature
        sig = inspect.signature(self.execute)
        parameters = {}

        for param_name, param in sig.parameters.items():
            if param_name == 'kwargs':
                continue

            param_type = self._get_param_type(param)
            required = param.default == inspect.Parameter.empty
            default = None if required else param.default

            # Check if parameter has type hints
            if param.annotation != inspect.Parameter.empty:
                param_type = self._annotation_to_string(param.annotation)

            parameters[param_name] = ToolParameter(
                name=param_name,
                type=param_type,
                description=getattr(param, 'description', f"Parameter {param_name}"),
                required=required,
                default=default
            )

        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters=parameters
        )

    def _get_param_type(self, param: inspect.Parameter) -> str:
        """Get parameter type as string."""
        if param.annotation != inspect.Parameter.empty:
            return self._annotation_to_string(param.annotation)
        return "string"

    def _annotation_to_string(self, annotation) -> str:
        """Convert type annotation to string representation."""
        if hasattr(annotation, '__name__'):
            return annotation.__name__
        elif hasattr(annotation, '_name'):
            return annotation._name
        elif str(annotation).startswith('typing.'):
            return str(annotation).replace('typing.', '').lower()
        else:
            return str(annotation).lower()

    def validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """Validate tool parameters.

        Args:
            **kwargs: Parameters to validate

        Returns:
            Dict of validated parameters

        Raises:
            ValueError: If validation fails
        """
        definition = self.get_definition()

        # Check required parameters
        for param_name, param_def in definition.parameters.items():
            if param_def.required and param_name not in kwargs:
                raise ValueError(f"Required parameter '{param_name}' is missing")

        # Type validation (basic)
        validated = {}
        for key, value in kwargs.items():
            if key in definition.parameters:
                param_def = definition.parameters[key]
                # Basic type checking - can be enhanced
                validated[key] = value
            else:
                self.logger.warning(f"Unknown parameter '{key}' for tool '{self.name}'")
                validated[key] = value

        return validated

    async def _execute_with_error_handling(self, **kwargs) -> ToolResult:
        """Execute tool with error handling wrapper."""
        try:
            self.logger.debug(f"Executing tool '{self.name}' with params: {kwargs}")
            validated_params = self.validate_parameters(**kwargs)
            result = await self.execute(**validated_params)
            self.logger.debug(f"Tool '{self.name}' completed successfully")
            return result
        except ValidationError as e:
            error_msg = f"Parameter validation failed: {str(e)}"
            self.logger.error(error_msg)
            return ToolResult(success=False, error=error_msg)
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return ToolResult(success=False, error=error_msg)


class SyncTool(BaseTool):
    """Base class for synchronous tools."""

    @abstractmethod
    def execute_sync(self, **kwargs) -> ToolResult:
        """Execute the tool synchronously.

        Args:
            **kwargs: Tool parameters

        Returns:
            ToolResult: Execution result
        """
        pass

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool (async wrapper for sync tools)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute_sync, **kwargs)


class AsyncTool(BaseTool):
    """Base class for asynchronous tools."""

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool asynchronously.

        Args:
            **kwargs: Tool parameters

        Returns:
            ToolResult: Execution result
        """
        pass


# Parameter validation decorator
def tool_parameter(description: str):
    """Decorator to add parameter descriptions."""
    def decorator(func):
        if not hasattr(func, '__tool_params__'):
            func.__tool_params__ = {}
        # This is a simplified implementation
        # In a real implementation, you'd store parameter metadata
        return func
    return decorator


# Tool registration decorator
def register_tool(category: ToolCategory, name: Optional[str] = None, description: Optional[str] = None):
    """Decorator to register a tool class."""
    def decorator(cls):
        cls._tool_category = category
        cls._tool_name = name or cls.__name__.lower()
        cls._tool_description = description or cls.__doc__ or f"{cls.__name__} tool"
        return cls
    return decorator