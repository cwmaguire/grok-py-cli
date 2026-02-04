# MCP Client CLI Rewrite Implementation Plan

## Overview
You are grok-code-fast-1, an advanced LLM specialized in generating high-quality, efficient, and standards-compliant code. Your task is to implement a complete rewrite of the MCP (Model Context Protocol) client as a standalone CLI application. This rewrite must strictly adhere to the MCP specification version 2025-11-25, implementing HTTP transport over JSON-RPC 2.0 with Server-Sent Events (SSE) for notifications.
Project Structure & Phased Implementation Plan (Self-Advancing)
This project will be completed over multiple sessions. In each session, you MUST:

Determine exactly one logical next task that has not yet been completed, based on the current project state and the tasks already marked COMPLETE.
Clearly state what task number and description you are choosing to work on in this session.
Implement only that single task.
Output the complete, relevant code for that task (new files or updated existing ones).
Include necessary imports, models, functions, docstrings, and comments referencing the spec.
At the end of your response, explicitly state:
TASK [X] COMPLETE
(where [X] is the task number you just finished)

Do not implement more than one task per response. Do not skip ahead or combine tasks. Maintain consistency: reuse models, patterns, naming conventions, and state management approaches from previously completed tasks.
Previously Completed Tasks
Guidance for Choosing the Next Task
Choose the most foundational, smallest, and most logical next step that builds directly on completed work. Example progression order (use this as a loose guide only — you decide the exact next task):

Task 2: Implement basic HTTP client session and JSON-RPC request sender
Task 3: Add configuration (server URL, persistent config file, CLI args/env vars)
Task 4: Implement SSE listener / notification handler (background thread or async)
Task 5: Implement the initialize handshake and capability storage
Task 6: Add session / state management (session ID, capabilities cache)
Task 7: Implement the first real CLI group and command skeleton (using click)
Task 8: Implement ping command
Task 9: Implement resources/list command
… and so on, moving toward tools, sampling, tasks, etc.

In this session, decide what the single next task should be, name it clearly (assign the next sequential number), describe it briefly, implement it completely, and mark it done.
Begin now.
After completing the task you choose, end your response with:
TASK [X] COMPLETE

**Key Changes from Current Implementation:**
- Replace the current MCP library usage with direct HTTP/JSON-RPC implementation
- Use click instead of typer for CLI structure
- Use requests instead of httpx for HTTP client
- Use sseclient-py for SSE handling instead of custom aiosseclient
- Use pydantic for all data models and validation
- Use rich for terminal output formatting
- Implement all required commands from the specification
- Add proper session management and async task handling

## Step 1: Project Setup and Dependencies
Create a new directory structure for the MCP CLI client:
```
mcp_cli/
├── mcp_cli/
│   ├── __init__.py
│   ├── cli.py          # Main CLI entry point with click
│   ├── client.py       # HTTP client and session management
│   ├── models.py       # Pydantic models from MCP schema
│   ├── sse_handler.py  # SSE notification handling
│   └── config.py       # Configuration management
├── setup.py            # Package setup
├── pyproject.toml      # uv project configuration
├── README.md           # Usage instructions
└── requirements.txt    # Dependencies
```

Dependencies to include:
- click>=8.0.0
- requests>=2.25.0
- sseclient-py>=1.7.0
- pydantic>=2.0.0
- rich>=10.0.0
- pyyaml>=6.0.0 (for config)

## Step 1: Create project directory structure TASK [1] COMPLETE

## Step 2: Define Pydantic Models (models.py)
Implement all required models from the MCP schema exactly as specified. Use the schema definitions provided in mcp_rewrite.md:

```python
from typing import Union, List, Dict, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum

RequestId = Union[str, int]

class JSONRPCRequest(BaseModel):
    jsonrpc: str = Field("2.0")
    id: RequestId
    method: str
    params: Optional[Dict] = None

class JSONRPCResponse(BaseModel):
    jsonrpc: str = Field("2.0")
    id: RequestId
    result: Optional[Dict] = None
    error: Optional[Dict[str, Union[int, str, Dict]]] = None

class JSONRPCNotification(BaseModel):
    jsonrpc: str = Field("2.0")
    method: str
    params: Optional[Dict] = None

# Define all other models: Role, Annotations, ContentBlock subtypes,
# Resource, Tool, Prompt, Task, ClientCapabilities, etc.
# Follow the schema exactly from https://github.com/modelcontextprotocol/specification/blob/main/schema/2025-11-25/schema.py
```

## Step 3: Implement HTTP Client (client.py)
Create an HTTP client class that handles:
- Session management with session IDs
- JSON-RPC request construction and sending
- Response parsing and validation
- Error handling for HTTP and JSON-RPC errors

Key methods:
- `initialize()`: Send initialize request and store session ID
- `send_request()`: Generic method for sending JSON-RPC requests
- `send_notification()`: For sending notifications (if needed)

## Step 4: Implement SSE Handler (sse_handler.py)
Create an SSE handler for receiving notifications:
- Use sseclient-py to connect to GET /mcp endpoint
- Handle incoming notifications in background threads
- Parse JSON-RPC notification messages
- Provide callback mechanism for notification processing


## Step 5: Implement CLI Structure (cli.py) TASK [5] COMPLETE
Use click to create the main CLI group and all commands:

```python
import click
from rich.console import Console
from rich.table import Table

console = Console()

@click.group()
@click.option('--server-url', default='http://localhost:8000/mcp', help='MCP server URL')
@click.pass_context
def cli(ctx, server_url):
    ctx.ensure_object(dict)
    ctx.obj['server_url'] = server_url
    ctx.obj['session_id'] = None  # To be set after init

# Implement each command as @cli.command()
```

## Step 6: Implement Individual Commands
Follow the specification exactly for each command:

### init Command
- Send initialize request with ClientCapabilities
- Parse server capabilities response
- Store session ID for subsequent requests
- Display server info using rich tables

### ping Command
- Send ping request
- Display response

### resources-list Command
- Send resources/list with optional cursor/limit
- Display results in rich table format

### resources-read Command
- Send resources/read with URI
- Handle text and blob content appropriately

### tools-list Command
- Send tools/list
- Display tools in table format

### tools-call Command
- Send tools/call with async support
- If async, poll for completion or listen to SSE
- Display results or task ID

### prompts-list, sample-message, tasks-* Commands
- Implement following the same patterns

### subscribe Command
- Send resources/subscribe
- Start background SSE listener for notifications

## Step 7: Configuration Management (config.py)
- Store session state (session_id, server_url) in ~/.mcp-cli/config.json
- Load/save configuration automatically
- Handle multiple server configurations if needed

## Step 8: Error Handling and Logging
- Implement comprehensive error handling for:
  - HTTP connection errors
  - JSON-RPC errors (-32600, etc.)
  - Timeout errors
  - Validation errors
- Use logging with appropriate levels
- Display user-friendly error messages with rich

## Step 9: Rich Output Formatting
- Use rich Console, Table, Progress for all output
- Color-code success/error states
- Show progress bars for long-running operations
- Format JSON responses nicely

## Step 10: Testing and Documentation
- Add comprehensive docstrings with examples
- Create unit tests for each component
- Include integration tests with mock server
- Document all commands and options in README

## Implementation Guidelines
1. **Strict Spec Adherence**: Do not deviate from the MCP specification. Use only the provided schema and references.
2. **Library Usage**: Use exactly the specified libraries (click, requests, sseclient-py, pydantic, rich).
3. **Python Version**: Target Python 3.11.9 exactly.
4. **Code Quality**: Write clean, well-documented, type-hinted code.
5. **Error Handling**: Handle all edge cases gracefully.
6. **User Experience**: Make the CLI intuitive with helpful error messages and progress indicators.
7. **Async Support**: Implement proper async handling for long-running operations using threading where needed.
8. **Session Management**: Maintain session state across command invocations.
9. **Extensibility**: Design for easy addition of new commands or features.

## Validation Checklist
- [ ] All Pydantic models match schema exactly
- [ ] HTTP client sends proper JSON-RPC 2.0 requests
- [ ] SSE handler receives and parses notifications correctly
- [ ] All required CLI commands implemented
- [ ] Session ID handling works across commands
- [ ] Error handling covers all failure modes
- [ ] Rich output provides good user experience
- [ ] Configuration persists correctly
- [ ] Async operations work with polling/SSE
- [ ] Code passes type checking and linting
- [ ] Tests cover all functionality
- [ ] Documentation is complete

## References
Use these references embedded in your knowledge:
- MCP Specification: https://modelcontextprotocol.io/specification/2025-11-25
- Schema: https://github.com/modelcontextprotocol/specification/blob/main/schema/2025-11-25/schema.py
- Quickstart: https://modelcontextprotocol.io/docs/develop/build-client
- Development Guide: https://github.com/cyanheads/model-context-protocol-resources/blob/main/guides/mcp-client-development-guide.md
