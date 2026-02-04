#!/usr/bin/env python3
"""Simple script to test MCP connection with longer timeout"""

import asyncio
import sys
import os

# Add the project root to path so we can import grok_py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grok_py.mcp.client import MCPClient

async def main():
    print("Testing MCP connection to http://127.0.0.1:8000/mcp with 60s timeout")

    # Use longer timeout
    client = MCPClient("http://127.0.0.1:8000/mcp", connect_timeout=60.0)

    try:
        print("Connecting...")
        connected = await client.connect()
        if not connected:
            print("Failed to connect")
            return

        print("Connected successfully. Listing tools...")
        tools = await client.list_tools()
        print(f"Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())