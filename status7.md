# Grok CLI Project Status Update 7

## Project Overview
This is the Grok CLI project (grok-py-cli), a Python-based command-line interface extending Grok AI with file editing, coding, and system operations. The project includes MCP (Model Context Protocol) integration for extending functionality via external servers, with sandboxed Docker-based execution for security. Recent sessions have focused on debugging and fixing MCP tool execution issues.

## Current Setup
- **Python Management**: Using `uv` for dependency management, virtual environments, and all Python-related operations. The project is installed in an editable mode within a uv-managed venv at `.venv`.
- **Installation**: `uv pip install -e .` from the project root installs grok-py and dependencies in the isolated venv.
- **Activation**: Always activate the venv with `source .venv/bin/activate` before running grok-py commands. The system Python (pyenv) is not used to avoid conflicts.
- **MCP Integration**: Configured to connect to an HTTP-based MCP server at `http://127.0.0.1:8000/mcp`. The server is a custom implementation called "mcp-screenshot-server" from a separate project at `/home/c/dev/mcp_screenshot/`. The client uses FastMCP's `streamable-http` (SSE) transport. MCP configuration is stored in `~/.grok/mcp_config.yaml` (not in project settings), with servers discovered and registered on CLI startup. Tool execution is sandboxed in Docker containers with host network mode to allow localhost access.

## Recent Developments and Issues
- **MCP Configuration**: Discovered that MCP servers are configured via `~/.grok/mcp_config.yaml` using the `grok mcp add-server` command, rather than project-settings.json. The screenshot server is configured as "my-server" with URL `http://127.0.0.1:8000/mcp`.
- **Server Management**: The MCP server must be started separately using `/home/c/dev/mcp_screenshot/.venv/bin/python3 /home/c/dev/mcp_screenshot/server.py`. It runs on `http://127.0.0.1:8000` and provides `hello` and `take_screenshot` tools.
- **Tool Discovery**: On CLI startup, MCP clients are created, connected, and tools are discovered. Logs show "• my-server: 2 tools discovered" when successful. Connection failures occur if the server is not running or network issues exist.
- **Sandbox Execution**: MCP tools execute in Docker containers for security. The container uses host network mode to access localhost services. However, the `take_screenshot` tool fails because scrot requires X11 server access, which is not available in the sandbox (even with host networking, as X11 sockets are not shared).
- **Current Status**: Tool discovery works when the server is running, but execution fails due to X11 access issues in the sandbox. Potential fixes include mounting X11 sockets and setting DISPLAY in the container config, but this reduces security.

## Next Steps
- Resolve X11 access for screenshot tool execution in the sandbox.
- Test tool execution after fixes.
- Consider alternative screenshot methods that don't require X11.

1. Do not edit the mcp_screenshot project. 2. do not stop or start the mcp_screenshot server: tell me and I'll do it. [end of instructions for status file]