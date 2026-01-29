"""Tool definitions for Grok API interactions."""

from typing import Any, Dict, List, Optional


def create_tool_definition(
    name: str,
    description: str,
    parameters: Dict[str, Any],
    required: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create a tool definition for the Grok API.

    Args:
        name: Tool name.
        description: Tool description.
        parameters: Parameter schema.
        required: List of required parameters.

    Returns:
        Tool definition dictionary.
    """
    tool_def = {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
            }
        }
    }

    if required:
        tool_def["function"]["parameters"]["required"] = required

    return tool_def


# File operations tools
FILE_EDITOR_TOOL = create_tool_definition(
    name="file_editor",
    description="Read, create, edit, or delete files. Use this for file operations.",
    parameters={
        "operation": {
            "type": "string",
            "enum": ["read", "write", "edit", "delete"],
            "description": "File operation to perform"
        },
        "path": {
            "type": "string",
            "description": "File path"
        },
        "content": {
            "type": "string",
            "description": "Content for write/edit operations"
        },
        "start_line": {
            "type": "integer",
            "description": "Starting line number for partial reads (optional)"
        },
        "end_line": {
            "type": "integer",
            "description": "Ending line number for partial reads (optional)"
        }
    },
    required=["operation", "path"]
)

SEARCH_TOOL = create_tool_definition(
    name="search",
    description="Search for text or files in the codebase.",
    parameters={
        "query": {
            "type": "string",
            "description": "Search query or file pattern"
        },
        "include_pattern": {
            "type": "string",
            "description": "File pattern to include (e.g., '*.py')"
        },
        "exclude_pattern": {
            "type": "string",
            "description": "File pattern to exclude"
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results to return"
        }
    },
    required=["query"]
)

# System tools
BASH_TOOL = create_tool_definition(
    name="bash",
    description="Execute shell commands.",
    parameters={
        "command": {
            "type": "string",
            "description": "Shell command to execute"
        },
        "working_directory": {
            "type": "string",
            "description": "Working directory for command execution"
        },
        "timeout": {
            "type": "integer",
            "description": "Command timeout in seconds"
        }
    },
    required=["command"]
)

# Development tools
CODE_EXECUTION_TOOL = create_tool_definition(
    name="code_execution",
    description="Execute code in a safe sandbox environment.",
    parameters={
        "code": {
            "type": "string",
            "description": "Code to execute"
        },
        "language": {
            "type": "string",
            "enum": ["python", "javascript", "java", "cpp", "go", "rust", "bash"],
            "description": "Programming language"
        },
        "input": {
            "type": "string",
            "description": "Input to provide to the code"
        },
        "timeout": {
            "type": "integer",
            "description": "Execution timeout in seconds"
        }
    },
    required=["code", "language"]
)

WEB_SEARCH_TOOL = create_tool_definition(
    name="web_search",
    description="Search the web for current information.",
    parameters={
        "query": {
            "type": "string",
            "description": "Search query"
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results to return"
        }
    },
    required=["query"]
)

# Default tool set
DEFAULT_TOOLS = [
    FILE_EDITOR_TOOL,
    SEARCH_TOOL,
    BASH_TOOL,
    CODE_EXECUTION_TOOL,
    WEB_SEARCH_TOOL,
]