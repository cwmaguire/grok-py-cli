"""
UI Module for Grok CLI Python Implementation

This module provides the terminal user interface components using Rich library,
including chat interface, input handling, and various UI components.
"""

from .chat_interface import ChatInterface
from .input import InputHandler
from .components.progress import ProgressIndicator
from .components.confirm import EnhancedConfirmationDialog, ConfirmationHistory, ConfirmationRecord
from .components.prompt import UserPromptSystem, InputValidator, TextValidator, NumericValidator, PathValidator, ValidationError
from .components.status import StatusDisplay
from .components.confirm import ConfirmationDialog

# New streaming and parsing components
from .streaming import StreamingResponseProcessor
from .parser import ResponseParser, ParsedResponse, ResponseType
from .updates import RealTimeUpdateManager, UIState, UpdatePriority
from .caching import ResponseCache, HistoryManager, CachedResponse, HistoryEntry

# Advanced input handling components
from .input_handler import AdvancedInputHandler, ValidationResult
from .validator import InputValidator
from .buffer import InputBufferManager, BufferState

__all__ = [
    "ChatInterface",
    "InputHandler",
    "ProgressIndicator",
    "StatusDisplay",
    "ConfirmationDialog",
    # New components
    "StreamingResponseProcessor",
    "ResponseParser",
    "ParsedResponse",
    "ResponseType",
    "RealTimeUpdateManager",
    "UIState",
    "UpdatePriority",
    "ResponseCache",
    "HistoryManager",
    "CachedResponse",
    "HistoryEntry",
    # Advanced input components
    "AdvancedInputHandler",
    "ValidationResult",
    "InputValidator",
    "InputBufferManager",
    "BufferState",
]