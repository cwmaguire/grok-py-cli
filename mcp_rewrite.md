You are grok-code-fast-1, an advanced LLM specialized in generating high-quality, efficient, and standards-compliant code. Your task is to implement an LLM CLI (Command-Line Interface) that acts as a client to the MCP (Model Context Protocol) server based on the following detailed specification. This specification is derived from the latest official MCP standards as of February 2026, specifically version 2025-11-25. You must adhere strictly to this spec without deviations, assumptions, or additions unless explicitly allowed. Ignore any prior knowledge or lookups; use only the details provided here. The CLI must integrate with the MCP server implemented previously, allowing users to interact via commands to send requests, receive responses, and handle notifications.

### Core Objectives
- Implement a fully functional CLI client for MCP over HTTP, supporting JSON-RPC 2.0 requests via POST and receiving notifications via SSE (Server-Sent Events).
- The CLI should enable interaction with LLM features exposed by the server: listing and reading resources, listing and calling tools, listing prompts, generating messages via sampling, managing tasks (create, list, get, cancel), and handling subscriptions.
- Support both synchronous and asynchronous modes: for async, poll tasks or listen to SSE for updates.
- Ensure usability: Provide helpful command outputs, error handling, and progress indicators for long-running operations.
- Target language: Python 3.11.9, using libraries like click for CLI structure, requests for HTTP POST, sseclient-py for SSE handling, pydantic for model validation, and rich for pretty-printing outputs.
- Dependency management: Use uv for creating virtual environments and installing dependencies. Include a setup script or instructions for uv.
- The CLI should be minimal but complete: Include help texts, logging, and support for server URL configuration (default: http://localhost:8000/mcp).
- Integration: Allow chaining commands or scripting for LLM workflows, e.g., initialize, list tools, call a tool, sample a message.

### Key References and Up-to-Date Documentation
Use these as your sole sources for protocol details. Do not perform external lookups; embed relevant excerpts in your code comments.
- Official Specification: https://modelcontextprotocol.io/specification/2025-11-25 – This defines the authoritative requirements, based on the schema at https://github.com/modelcontextprotocol/specification/blob/main/schema/2025-11-25/schema.py (adapted for Python).
- Schema JSON: https://raw.githubusercontent.com/modelcontextprotocol/specification/main/schema/2025-11-25/schema.json – Use this for all type definitions and validation; implement with Pydantic.
- Quickstart for Clients: https://modelcontextprotocol.io/docs/develop/build-client – Guides on basic setup, including HTTP transport and SSE.
- GitHub Repo: https://github.com/modelcontextprotocol/specification – Contains schema.py for Python type hints.
- Development Guide: https://github.com/cyanheads/model-context-protocol-resources/blob/main/guides/mcp-client-development-guide.md – Practical examples for sending requests and handling SSE.
- Spring AI Reference (for conceptual inspiration, not implementation): https://docs.spring.io/spring-ai/reference/api/mcp/mcp-overview.html – Shows client-side request patterns.
- .NET Blog (conceptual): https://devblogs.microsoft.com/dotnet/build-a-model-context-protocol-mcp-client-in-csharp – Demonstrates initialization and tool calls.
- Cloudflare Guide (HTTP focus): https://blog.cloudflare.com/remote-model-context-protocol-clients-mcp – Explains SSE consumption for notifications.

### Protocol Overview (Targeted for Implementation)
MCP is JSON-RPC 2.0 based, transport-agnostic, but you must implement client over HTTP:
- **Endpoint**: POST to `/mcp` for requests; GET to `/mcp` with query params (e.g., ?session_id=...) for SSE notifications.
- **Messages**: Construct JSON objects with `jsonrpc: "2.0"`, `id` (unique per request), `method`, `params`.
- **Responses**: Parse JSON-RPC responses for `result` or `error`.
- **Notifications**: Listen to SSE (event: message, data: JSON notification); handle in background threads if needed.
- **Errors**: Log and display JSON-RPC errors (e.g., code -32600 for invalid request).
- **Sessions**: Maintain session state via client-generated IDs; include in requests if required.
- **Capabilities Negotiation**: Send client capabilities in `initialize`; parse server capabilities from response.

Extracted Key Schema Elements (Implement These Types Exactly):
```python
# From schema.py – Define these as Pydantic models in your code for validation and serialization.
from typing import Union, List, Dict, Optional, Literal
from pydantic import BaseModel, Field

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

# Annotations (for resources, tools, etc.)
Role = Literal["user", "assistant", "system"]
class Annotations(BaseModel):
    audience: Optional[List[Role]] = None
    lastModified: Optional[str] = None
    priority: Optional[int] = None

# Content Blocks (for messages, tools)
# Define subtypes like TextContent, ImageContent, etc., as separate BaseModels per schema.
ContentBlock = Union["TextContent", "ImageContent", "AudioContent", "ToolCallContent", "ResourceLink"]  # Use update_forward_refs() or separate classes.

# Resources
class Resource(BaseModel):
    name: str
    title: Optional[str] = None
    uri: str
    mimeType: Optional[str] = None
    description: Optional[str] = None
    size: Optional[int] = None
    icons: Optional[List["Icon"]] = None  # Define Icon as BaseModel.
    annotations: Optional[Annotations] = None

# Tools
class Tool(BaseModel):  # Extend from a BaseMetadata if defined.
    description: str
    parameters: Dict  # JSONSchema dict per Draft 2020-12.
    returns: Optional[Dict] = None  # JSONSchema.

# Prompts
class Prompt(BaseModel):  # Extend from BaseMetadata.
    description: str
    messages: List["PromptMessage"]  # Define PromptMessage.
    arguments: Optional[List["PromptArgument"]] = None  # Define PromptArgument.

# Tasks
TaskStatus = Literal["working", "input_required", "completed", "failed", "cancelled"]
class Task(BaseModel):
    taskId: str
    status: TaskStatus
    statusMessage: Optional[str] = None
    createdAt: str
    lastUpdatedAt: str
    ttl: Optional[int] = None
    pollInterval: Optional[int] = None

# Capabilities (Client sends these)
class ClientCapabilities(BaseModel):
    experimental: Optional[Dict[str, Dict]] = None
    logging: Optional[Dict] = None
    completions: Optional[Dict] = None
    prompts: Optional[Dict[str, bool]] = Field(default_factory=lambda: {"listChanged": True})
    resources: Optional[Dict[str, bool]] = Field(default_factory=lambda: {"subscribe": True, "listChanged": True})
    tools: Optional[Dict[str, bool]] = Field(default_factory=lambda: {"listChanged": True})
    tasks: Optional[Dict[str, Dict]] = Field(default_factory=lambda: {
        "list": {},
        "cancel": {},
        "requests": {"tools": {"call": {}}, "sampling": {"createMessage": {}}}
    })
    # Add more as needed.
```

### Required Commands to Implement (CLI Structure)
Implement these as click commands. Each command constructs a JSON-RPC request, sends via POST, parses response with Pydantic, and displays using rich (e.g., tables for lists). Support --async flag for task-based operations. Use a global session ID after initialize.
1. **init** (Initialize session)
   - Options: --server-url (default: http://localhost:8000/mcp)
   - Send: initialize with clientInfo (e.g., {"name": "LLM-CLI", "version": "1.0"}), capabilities: ClientCapabilities.
   - Output: Server info, capabilities; store session ID if provided.

2. **ping** (Health check)
   - Send: ping.
   - Output: Pong response.

3. **resources-list** (List resources)
   - Options: --cursor, --limit
   - Send: resources/list with params.
   - Output: Table of resources (name, uri, description).

4. **resources-read** (Read resource)
   - Args: uri
   - Send: resources/read with {uri}.
   - Output: Contents (text or base64 decoded if blob).

5. **tools-list** (List tools)
   - Options: --cursor, --limit
   - Send: tools/list.
   - Output: Table of tools (name, description).

6. **tools-call** (Call tool)
   - Args: tool_name
   - Options: --args (JSON string), --async (bool), --task-id (if resuming)
   - Send: tools/call with {toolName, arguments, taskId if async}.
   - Output: Result if sync; taskId if async. If async, poll or listen to SSE for completion.

7. **prompts-list** (List prompts)
   - Options: --cursor, --limit
   - Send: prompts/list.
   - Output: Table of prompts (description, messages summary).

8. **sample-message** (Create message via sampling)
   - Options: --messages (JSON list), --options (JSON dict), --async (bool), --task-id
   - Send: sampling/createMessage with params.
   - Output: Generated message if sync; taskId if async. Support streaming if options specify.

9. **tasks-list** (List tasks)
   - Options: --filter (JSON)
   - Send: tasks/list.
   - Output: Table of tasks (id, status, createdAt).

10. **tasks-get** (Get task)
    - Args: task_id
    - Send: tasks/get.
    - Output: Task details.

11. **tasks-cancel** (Cancel task)
    - Args: task_id
    - Send: tasks/cancel.
    - Output: Confirmation.

12. **subscribe** (Subscribe to resource)
    - Args: uri
    - Send: resources/subscribe if supported.
    - Output: Subscription ID; start SSE listener in background to print notifications.

### Implementation Structure
- Use click: from click import group, command, option, argument; @group() def cli(): ...
- HTTP Client: Use requests.Session for persistent connections; POST JSONRPCRequest.dict().
- SSE Handling: Use sseclient.SSEClient for GET /mcp; run in thread for background notifications.
- Validation: Serialize requests with Pydantic .dict(); parse responses into models.
- State Management: Use a config file (e.g., ~/.llm-cli-config.json) for session ID, server URL.
- Logging: Use logging module with INFO level; integrate with rich for console output.
- Dependency Setup: Include a setup.py or README with uv commands: uv venv; uv pip install click requests sseclient-py pydantic rich.
- Entry Point: If __name__ == "__main__": cli()
- Error Handling: Catch HTTP errors, JSON-RPC errors; display user-friendly messages.
- Extensibility: Allow custom methods via a generic --method --params command.
- Testing: Include example usage in docstrings; simulate server if needed.

### Additional Directives
- Generate complete, runnable code: Include all imports, models, commands, and CLI setup.
- Efficiency: Use threading for SSE to keep CLI responsive.
- Security: Validate user inputs; handle sensitive data carefully.
- Documentation: Add docstrings and help texts referencing the spec URLs.
- No Extras: Do not add server code; focus on client. Keep minimal.
