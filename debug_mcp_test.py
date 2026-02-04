#!/usr/bin/env python3
"""Test script to try standard SSE MCP connection flow"""

import asyncio
import sys
import os
import logging

# Enable logging
logging.basicConfig(level=logging.DEBUG)

# Add the project root to path so we can import grok_py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client

async def test_hybrid_sse():
    """Test hybrid flow: POST initialize to get session ID, then SSE with session ID, skip session initialize"""
    url = "http://127.0.0.1:8000/mcp"

    print("Testing hybrid SSE connection to", url)

    try:
        # First, POST initialize to get session ID
        async with httpx.AsyncClient() as client:
            init_data = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "grok-py", "version": "0.1.0"}
                }
            }
            headers = {"Accept": "application/json, text/event-stream"}
            response = await client.post(url, json=init_data, headers=headers)
            response.raise_for_status()
            session_id = response.headers.get("mcp-session-id")
            print(f"Got session ID: {session_id}")

            # Now establish SSE with session ID
            async with sse_client(url, headers={'Accept': 'text/event-stream', 'Mcp-Session-Id': session_id}) as (read, write):
                print("SSE connection established")
                session = ClientSession(read, write)
                print("Initializing session (even though already done via POST)...")
                # Try initialize again over SSE
                result = await session.initialize()
                print("Initialize result:", result)
                print("Listing tools...")
                tools = await session.list_tools()
                print(f"Found {len(tools.tools)} tools")
                for tool in tools.tools:
                    print(f"  - {tool.name}: {tool.description}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await test_hybrid_sse()

if __name__ == "__main__":
    asyncio.run(main())