#!/usr/bin/env python3
"""Simple script to test MCP connection and list tools from http://127.0.0.1:8000/mcp"""

import asyncio
import sys
import os
import json

# Add the project root to path so we can import grok_py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grok_py.mcp.client import MCPClient

async def main():
    print("Testing MCP connection to http://127.0.0.1:8000/mcp")

    client = MCPClient("http://127.0.0.1:8000/mcp")

    try:
        print("Connecting...")
        connected = await client.connect()
        if not connected:
            print("Failed to connect")
            return

        print("Connected successfully.")
        print("Listing tools...")

        # Get the raw response by accessing the internal method or modifying
        # Since list_tools returns parsed, let's do the HTTP request manually
        import httpx
        async with httpx.AsyncClient() as http_client:
            # List tools
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

            # Now parse as usual
            tools_data = rpc_result["result"]["tools"]
            tools = []
            for tool in tools_data:
                tools.append(tool)

            print(f"\nParsed {len(tools)} tools:")
            for tool in tools:
                print(f"  - {tool['name']}: {tool['description']}")

            # Now call the take_screenshot tool
            print("\nCalling take_screenshot tool...")
            tool_name = "take_screenshot"
            params = {"mode": "description"}  # Default mode

            # Do the HTTP request manually for tools/call
            call_data = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": params
                }
            }
            headers = {"Accept": "application/json, text/event-stream"}
            if client.session_id:
                headers["Mcp-Session-Id"] = client.session_id

            response = await http_client.post("http://127.0.0.1:8000/mcp", json=call_data, headers=headers)
            response.raise_for_status()
            try:
                call_result = response.json()
            except:
                text = response.text
                if 'data: ' in text:
                    data_str = text.split('data: ')[1].strip()
                    call_result = json.loads(data_str)
                else:
                    print("Raw call response text:", text)
                    raise ValueError("Invalid call response format")

            print("Full MCP server response for tools/call:")
            print(json.dumps(call_result, indent=2))

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())