# MCP (Model Context Protocol) Integration

Grok CLI supports the Model Context Protocol (MCP), an open protocol that enables AI models to connect to external tools, data sources, and services in a standardized way. This allows you to extend Grok CLI with custom tools and integrations.

## Overview

MCP integration in Grok CLI allows you to:
- Connect to MCP-compatible servers
- Discover and use tools provided by those servers
- Execute tools securely in isolated environments
- Manage tool configurations and parameters

## Quick Start

### 1. Add an MCP Server

To start using MCP tools, first add an MCP server:

```bash
# Add a stdio-based MCP server (runs as a subprocess)
grok-py mcp add-server my-git-server --command git-mcp-server

# Add an HTTP-based MCP server
grok-py mcp add-server my-linear-server --url https://api.linear.app/mcp
```

### 2. List Available Servers

Check your configured servers:

```bash
grok-py mcp list-servers
```

### 3. Discover Tools

List all available MCP tools from configured servers:

```bash
grok-py mcp list-tools
```

### 4. Use MCP Tools in Chat

Once configured, MCP tools are automatically available in chat mode:

```bash
grok-py chat "Use the git server to get the status of the current repository"
```

## Configuration

MCP servers are configured in `~/.grok/mcp_config.json`. You can also manage them via CLI commands.

### Configuration File Format

```json
{
  "servers": {
    "my-git-server": {
      "type": "stdio",
      "command": "git-mcp-server",
      "args": ["--verbose"],
      "timeout": 30.0,
      "max_retries": 3
    },
    "linear-api": {
      "type": "http",
      "url": "https://api.linear.app/mcp",
      "timeout": 60.0,
      "max_retries": 5
    }
  }
}
```

### Server Types

#### Stdio Servers
Run MCP servers as subprocesses communicating via stdin/stdout:

```bash
grok-py mcp add-server git-tools --command git-mcp-server --args "--repo /path/to/repo"
```

#### HTTP Servers
Connect to MCP servers over HTTP:

```bash
grok-py mcp add-server linear --url https://api.linear.app/mcp --timeout 60
```

## Examples

### Example 1: Git Repository Management

Add a git MCP server and use it to manage repositories:

```bash
# Add git server
grok-py mcp add-server git-server --command git-mcp-server --args "--repo ."

# Use in chat
grok-py chat "Show me the git status and recent commits"
```

### Example 2: Linear Issue Tracking

Connect to Linear's MCP server for issue management:

```bash
# Add Linear server (requires API key in environment)
grok-py mcp add-server linear --url https://api.linear.app/mcp

# Query issues
grok-py chat "Show me all open issues assigned to me"
```

### Example 3: Custom Tool Development

Create your own MCP server:

```python
# custom_server.py
from mcp import Server, Tool
import asyncio

server = Server("custom-tools")

@server.tool()
async def get_weather(city: str) -> str:
    """Get weather for a city."""
    # Implementation here
    return f"Weather in {city}: Sunny, 72°F"

if __name__ == "__main__":
    asyncio.run(server.run())
```

Add it to Grok CLI:

```bash
grok-py mcp add-server weather --command python --args "custom_server.py"
```

## Security

All MCP tool executions run in isolated Docker containers to ensure security:
- Tools cannot access your filesystem directly
- Network access is controlled
- Execution timeouts prevent hanging
- Input validation prevents malicious parameters

## Troubleshooting

### Server Connection Issues

If a server fails to connect:
1. Check server logs: `grok-py mcp list-servers`
2. Verify configuration: Ensure command/URL is correct
3. Test manually: Run the server command outside Grok CLI

### Tool Discovery Problems

If tools aren't showing up:
1. Ensure server is running and accessible
2. Check server configuration timeout values
3. Verify MCP protocol compatibility

### Performance Issues

For slow tool execution:
- Increase timeout values for slow servers
- Reduce max_retries if servers are unreliable
- Consider using HTTP servers for better performance

## Best Practices

1. **Use descriptive server IDs**: Choose clear names like `git-work` or `linear-personal`
2. **Set appropriate timeouts**: Start with 30s for stdio, 60s for HTTP
3. **Configure retries**: Use 3-5 retries for unreliable servers
4. **Test configurations**: Verify servers work before relying on them
5. **Keep servers updated**: Update MCP server versions regularly

## Supported MCP Servers

Popular MCP servers you can try:
- **Git**: Repository management and analysis
- **GitHub**: Issue and PR management
- **Linear**: Issue tracking and project management
- **Slack**: Team communication
- **Notion**: Document and knowledge management
- **Figma**: Design collaboration

For a complete list, check the [MCP Server Registry](https://github.com/modelcontextprotocol/registry).</content>
</xai:function_call">Create new file docs/mcp.md with the content above? (y/n) or provide alternative content: y