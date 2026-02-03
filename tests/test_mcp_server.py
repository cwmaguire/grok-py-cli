"""Simple test MCP server for testing MCP client functionality."""

import asyncio
import json
import sys
from typing import Any, Dict, List

from mcp import Server, Tool
from mcp.types import TextContent, PromptMessage
import mcp.server

# Create a simple MCP server
server = Server("test-server")


@server.tool()
async def add_numbers(a: int, b: int) -> int:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of the two numbers
    """
    return a + b


@server.tool()
async def get_weather(city: str) -> str:
    """Get weather information for a city.

    Args:
        city: Name of the city

    Returns:
        Weather information
    """
    # Mock weather response
    return f"Weather in {city}: Sunny, 72°F"


@server.tool()
async def search_files(pattern: str, directory: str = ".") -> List[str]:
    """Search for files matching a pattern.

    Args:
        pattern: File pattern to search for
        directory: Directory to search in

    Returns:
        List of matching files
    """
    # Mock file search
    return [f"file1.txt", f"file2.txt"]


if __name__ == "__main__":
    # Run the server
    import mcp.server.stdio

    async def main():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )

    asyncio.run(main())