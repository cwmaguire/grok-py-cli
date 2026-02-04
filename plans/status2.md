# Grok CLI Project Status Update

## Summary of Progress Since Initial Status

We have been troubleshooting MCP (Model Context Protocol) integration with an HTTP-based MCP server running at `http://127.0.0.1:8000/mcp`. The server appears to be a custom implementation called "mcp-screenshot-server" (version 1.26.0) from a separate project at `/home/c/dev/mcp_screenshot/`.

### Key Findings and Changes Made

1. **Initial Issues**: The original MCP client implementation attempted JSON-RPC over HTTP, which was rejected by the server with 406 Not Acceptable errors requiring `Accept: text/event-stream` header.

2. **Protocol Discovery**: Through curl testing, we discovered the server uses a hybrid protocol:
   - Initialize via POST with `Accept: application/json, text/event-stream` returns session establishment in SSE format
   - Subsequent operations require SSE connection with `Mcp-Session-Id` header

3. **Client Code Updates**:
   - Modified `grok_py/mcp/client.py` to handle HTTP connections by first POST-initializing to obtain session ID, then establishing SSE connection
   - Removed redundant `initialize()` call since session is already established via POST
   - Updated disconnect logic to properly close HTTP clients

4. **Current State**: The connection process now successfully completes POST initialize and GET SSE establishment (both return 200 OK), but the SSE stream disconnects after ~30 seconds despite server-side pings. The timeout occurs at the `sse_client().__aenter__()` level.

### Debug Script Logs

```
$python debug_mcp.py
Testing MCP connection to http://127.0.0.1:8000/mcp
Connecting...
2026-02-02 22:19:32,421 - httpx - INFO - HTTP Request: POST http://127.0.0.1:8000/mcp "HTTP/1.1 200 OK"
2026-02-02 22:19:32,430 - httpx - INFO - HTTP Request: GET http://127.0.0.1:8000/mcp "HTTP/1.1 200 OK"
2026-02-02 22:20:02,435 - grok_py.mcp.client - WARNING - Connection attempt 1 timed out
2026-02-02 22:20:02,436 - grok_py.mcp.client - INFO - Retrying connection in 1 seconds...
2026-02-02 22:20:03,452 - httpx - INFO - HTTP Request: POST http://127.0.0.1:8000/mcp "HTTP/1.1 200 OK"
2026-02-02 22:20:03,460 - httpx - INFO - HTTP Request: GET http://127.0.0.1:8000/mcp "HTTP/1.1 200 OK"
2026-02-02 22:20:33,465 - grok_py.mcp.client - WARNING - Connection attempt 2 timed out
[... repeated for attempts 3 and 4 ...]
2026-02-02 22:21:39,552 - grok_py.mcp.client - ERROR - Failed to connect after 4 attempts
Failed to connect
```

### Backend MCP Server Logs

```
DEBUG:mcp.server.streamable_http_manager:Creating new transport
INFO:mcp.server.streamable_http_manager:Created new transport with session ID: 8af1c9eb2c20462faf7e4d589a517365
INFO:     127.0.0.1:56234 - "POST /mcp HTTP/1.1" 200 OK
DEBUG:mcp.server.streamable_http:Closing SSE writer
DEBUG:sse_starlette.sse:chunk: b'event: message\r\ndata: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-11-25","capabilities":{"experimental":{},"prompts":{"listChanged":false},"resources":{"subscribe":false,"listChanged":false},"tools":{"listChanged":false}},"serverInfo":{"name":"mcp-screenshot-server","version":"1.26.0"}}}\r\n\r\n'
DEBUG:sse_starlette.sse:Got event: http.disconnect. Stop streaming.
DEBUG:mcp.server.streamable_http_manager:Session already exists, handling request directly
INFO:     127.0.0.1:56242 - "GET /mcp HTTP/1.1" 200 OK
DEBUG:sse_starlette.sse:ping: b': ping - 2026-02-03 06:19:47.430583+00:00\r\n\r\n'
DEBUG:sse_starlette.sse:ping: b': ping - 2026-02-03 06:19:47.430583+00:00\r\n\r\n'
DEBUG:sse_starlette.sse:Got event: http.disconnect. Stop streaming.
DEBUG:mcp.server.streamable_http:Closing standalone SSE writer
[... repeated for each attempt ...]
```

### Machine-Specific Observations

- **netstat command unavailable**: `netstat -tlnp` failed with "netstat: not found", requiring use of `ss -tlnp` instead
- **Python environment**: Properly configured with uv-managed venv at `.venv`
- **MCP server process**: Running from `/home/c/dev/mcp_screenshot/.venv/bin/python3 server.py` (PID varies, e.g., 1037438)
- **Server capabilities**: Based on initialize response, supports tools but no prompts or resources

### Next Steps for Investigation

The SSE connection establishes successfully but terminates prematurely. Potential causes:
1. `sse_client` from MCP library may not be compatible with this server's SSE implementation
2. Missing or incorrect headers in SSE request
3. Server expecting different keep-alive or heartbeat mechanism
4. Client-side timeout configuration issues

Investigate by examining the `sse_client` implementation or replacing it with manual httpx SSE handling if necessary.