#!/usr/bin/env python3
"""Script to test MCP connection, list tools, and call the take_screenshot tool"""

import asyncio
import sys
import os
import json

# Add the project root to path so we can import grok_py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grok_py.mcp.client import MCPClient
import httpx

async def main():
    print("Testing MCP connection to http://127.0.0.1:8000/mcp")

    client = MCPClient("http://127.0.0.1:8000/mcp", execute_timeout=60.0)

    try:
        print("Connecting...")
        connected = await client.connect()
        if not connected:
            print("Failed to connect")
            return

        print("Connected successfully.")

        async with httpx.AsyncClient() as http_client:
            # List tools
            print("Listing tools...")
            data = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
            headers = {"Accept": "application/json, text/event-stream"}
            if client.session_id:
                headers["Mcp-Session-Id"] = client.session_id

            response = await http_client.post("http://127.0.0.1:8000/mcp", json=data, headers=headers)
            response.raise_for_status()
            try:
                rpc_result = response.json()
            except:
                text = response.text
                if 'data: ' in text:
                    data_str = text.split('data: ')[1].strip()
                    rpc_result = json.loads(data_str)
                else:
                    print("Raw response text:", text)
                    raise ValueError("Invalid response format")

            print("Full MCP server response for tools/list:")
            print(json.dumps(rpc_result, indent=2))

            tools_data = rpc_result["result"]["tools"]
            print(f"\nFound {len(tools_data)} tools:")
            for tool in tools_data:
                print(f"  - {tool['name']}: {tool['description']}")

            # Call the take_screenshot tool using MCPClient.execute_tool
            print("\nCalling take_screenshot tool...")
            tool_name = "take_screenshot"
            params = {"mode": "description"}

            tool_result = await client.execute_tool(tool_name, params)
            print(f"Tool result: success={tool_result.success}, data length={len(tool_result.data) if tool_result.data else 0}")
            if tool_result.data:
                print("Tool data:")
                print(tool_result.data)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())