# MCP CLI

A comprehensive command-line interface for interacting with MCP (Model Context Protocol) servers. The MCP CLI implements the full MCP specification version 2025-11-25, providing both synchronous and asynchronous operations over HTTP with JSON-RPC 2.0 and Server-Sent Events.

## Features

- **Full MCP Protocol Support**: Implements all required MCP methods and capabilities
- **Rich Terminal UI**: Beautiful tables, progress indicators, and colored output
- **Session Management**: Persistent connections with automatic session handling
- **Real-time Notifications**: Subscribe to resource updates with SSE
- **Comprehensive Error Handling**: Detailed error messages and logging
- **Configuration Management**: Persistent settings and multiple server support

## Installation

### From Source

```bash
git clone <repository>
cd mcp-cli
pip install -e .
```

### Requirements

- Python 3.11+
- Dependencies automatically installed via pip

## Quick Start

1. **Initialize connection to an MCP server:**

```bash
mcp-cli --server-url http://localhost:8000/mcp init
```

2. **Explore available capabilities:**

```bash
mcp-cli resources-list
mcp-cli tools-list
mcp-cli prompts-list
```

3. **Interact with resources and tools:**

```bash
# Read a resource
mcp-cli resources-read "file:///example.txt"

# Call a tool
mcp-cli tools-call "calculator" --arguments '{"expression": "2 + 2"}'

# Get a prompt
mcp-cli prompts-get "code-review" --arguments '{"language": "python"}'
```

## Command Reference

### Core Commands

#### `init`
Initialize connection to an MCP server and establish session.

```bash
mcp-cli init
```

Displays server information, capabilities, and stores session for subsequent commands.

#### `ping`
Test connection to the MCP server.

```bash
mcp-cli ping
```

### Resource Management

#### `resources-list [--cursor CURSOR] [--limit LIMIT]`
List available resources with optional pagination.

```bash
mcp-cli resources-list
mcp-cli resources-list --limit 10
mcp-cli resources-list --cursor "next_page_token"
```

#### `resources-read <uri>`
Read content from a specific resource URI.

```bash
mcp-cli resources-read "file:///path/to/resource"
mcp-cli resources-read "http://example.com/data.json"
```

Supports both text and binary content types.

#### `subscribe <uri>`
Subscribe to real-time updates for a resource.

```bash
mcp-cli subscribe "file:///logs/app.log"
```

Starts background SSE listener for resource change notifications. Use Ctrl+C to stop.

### Tool Management

#### `tools-list`
List all available tools with their descriptions and parameters.

```bash
mcp-cli tools-list
```

#### `tools-call <name> --arguments JSON`
Execute a tool with JSON-formatted arguments.

```bash
mcp-cli tools-call "web-search" --arguments '{"query": "Python MCP", "limit": 5}'
mcp-cli tools-call "file-operations" --arguments '{"action": "read", "path": "/tmp/test.txt"}'
```

### Prompt Management

#### `prompts-list`
List available prompts and their required arguments.

```bash
mcp-cli prompts-list
```

#### `prompts-get <name> --arguments JSON`
Retrieve and display a prompt with optional parameterization.

```bash
mcp-cli prompts-get "coding-assistant"
mcp-cli prompts-get "translate" --arguments '{"from_lang": "en", "to_lang": "es", "text": "Hello world"}'
```

### Task Management

#### `tasks-list`
List currently running asynchronous tasks.

```bash
mcp-cli tasks-list
```

## Configuration

### Configuration File

Settings are stored in `~/.mcp-cli/config.json`:

```json
{
  "server_url": "http://localhost:8000/mcp",
  "session_id": "abc123",
  "servers": {
    "production": {
      "url": "https://api.example.com/mcp",
      "session_id": "def456"
    }
  }
}
```

### Environment Variables

- `MCP_SERVER_URL`: Default server URL (can be overridden with `--server-url`)

### Multiple Servers

Configure multiple servers for easy switching:

```bash
# Add server configurations to config.json
# Then use --server-url to switch between them
mcp-cli --server-url http://dev-server:8000/mcp init
mcp-cli --server-url https://prod-server.com/mcp tools-list
```

## Logging

The CLI provides comprehensive logging to `mcp_cli.log` with the following levels:

- **DEBUG**: Detailed request/response information
- **INFO**: General operations and status
- **WARNING**: Non-critical issues
- **ERROR**: Errors and failures

## Error Handling

The CLI provides user-friendly error messages for common issues:

- **Connection errors**: Server unreachable or network issues
- **Authentication errors**: Invalid credentials or session expired
- **Protocol errors**: MCP specification violations
- **Validation errors**: Invalid arguments or parameters

All errors are logged with full context for debugging.

## Architecture

### Components

- **`cli.py`**: Main command-line interface with Click
- **`client.py`**: HTTP client for JSON-RPC communication
- **`models.py`**: Pydantic models for MCP schema validation
- **`sse_handler.py`**: Server-Sent Events handler for notifications
- **`config.py`**: Configuration management and persistence

### Protocol Implementation

- **Transport**: HTTP POST for requests, GET for SSE notifications
- **Protocol**: JSON-RPC 2.0 with MCP method extensions
- **Authentication**: Bearer token support (configurable)
- **Session Management**: Automatic session establishment and renewal

## Development

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_models.py

# Run with coverage
python -m pytest --cov=mcp_cli
```

### Code Quality

```bash
# Type checking
mypy mcp_cli/

# Linting
flake8 mcp_cli/

# Formatting
black mcp_cli/
```

## Troubleshooting

### Common Issues

1. **Connection refused**: Ensure MCP server is running and accessible
2. **Session expired**: Re-run `init` to establish new session
3. **Invalid arguments**: Check JSON syntax with `python -m json.tool`
4. **Permission denied**: Verify server allows the requested operations

### Debug Mode

Enable detailed logging:

```bash
# Check logs
tail -f mcp_cli.log

# Run with verbose output
mcp-cli --verbose <command>
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## References

- [MCP Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [MCP Quickstart](https://modelcontextprotocol.io/docs/develop/build-client)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)