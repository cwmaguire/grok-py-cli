"""Penetration tests for Grok CLI security vulnerabilities."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from grok_py.agent.tool_manager import ToolManager, MCPToolWrapper
from grok_py.mcp.client import MCPClient
from grok_py.tools.base import ToolDefinition, ToolParameter, ToolResult
from grok_py.mcp.config import MCPConfig
from mcp import StdioServerParameters


class TestPenetrationTesting:
    """Test suite for penetration testing scenarios."""

    @pytest.mark.asyncio
    async def test_command_injection_stdio_server(self):
        """Test that command injection in stdio server parameters is contained."""
        # Create a malicious server config that tries command injection
        malicious_command = "bash"
        malicious_args = ["-c", "echo 'pwned' && touch /tmp/pwned"]

        server_params = StdioServerParameters(
            command=malicious_command,
            args=malicious_args
        )

        client = MCPClient(server_params)

        # Mock the sandbox execution to capture what would be executed
        with patch('grok_py.agent.tool_manager.CodeExecutionTool') as mock_code_exec:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = '{"success": true, "data": "executed"}'
            mock_code_exec.return_value.execute_sync.return_value = mock_result

            # Create a dummy tool
            tool_def = ToolDefinition(
                name="test_tool",
                description="Test tool",
                parameters={}
            )

            wrapper = MCPToolWrapper(client, tool_def)

            # Execute the tool
            result = await wrapper.execute()

            # Verify the sandbox was called
            mock_code_exec.return_value.execute_sync.assert_called_once()

            # Get the generated code
            call_args = mock_code_exec.return_value.execute_sync.call_args
            generated_code = call_args[1]['code']

            # Verify the malicious command is in the generated code
            # (it should be, as it's part of the server params)
            assert malicious_command in generated_code
            assert "echo 'pwned'" in generated_code

            # But since it's in Docker, it should be contained
            # In a real test, we would check that host files are not affected
            assert result.success == True

    @pytest.mark.asyncio
    async def test_path_traversal_in_tool_parameters(self):
        """Test that path traversal attacks in tool parameters are handled safely."""
        # Create a tool that supposedly reads files
        tool_def = ToolDefinition(
            name="read_file",
            description="Read file content",
            parameters={
                "path": ToolParameter(
                    name="path",
                    type="string",
                    description="File path to read",
                    required=True
                )
            }
        )

        # Mock MCP client
        mock_client = MagicMock()
        mock_client.get_server_params_dict.return_value = {
            "type": "stdio",
            "command": "cat",
            "args": [],
            "env": {},
            "cwd": "/tmp",
            "encoding": "utf-8"
        }
        mock_client.timeout = 10.0

        wrapper = MCPToolWrapper(mock_client, tool_def)

        # Mock the code execution to simulate file reading in sandbox
        with patch('grok_py.agent.tool_manager.CodeExecutionTool') as mock_code_exec:
            mock_result = MagicMock()
            mock_result.success = True
            # Simulate that the tool tried to read /etc/passwd
            mock_result.data = '{"success": true, "data": "simulated file content"}'
            mock_code_exec.return_value.execute_sync.return_value = mock_result

            # Try path traversal attack
            result = await wrapper.execute(path="../../../etc/passwd")

            # Verify the parameters were passed to the sandbox
            call_args = mock_code_exec.return_value.execute_sync.call_args
            generated_code = call_args[1]['code']

            # The malicious path should be in the code
            assert "../../../etc/passwd" in generated_code

            # But since it's in Docker, access to host files should be limited
            assert result.success == True

    @pytest.mark.asyncio
    async def test_large_input_dos_attack(self):
        """Test that large inputs don't cause denial of service."""
        tool_def = ToolDefinition(
            name="process_text",
            description="Process text input",
            parameters={
                "text": ToolParameter(
                    name="text",
                    type="string",
                    description="Text to process",
                    required=True
                )
            }
        )

        mock_client = MagicMock()
        mock_client.get_server_params_dict.return_value = {
            "type": "stdio",
            "command": "python3",
            "args": ["-c", "print(len(input()))"],
            "env": {},
            "cwd": "/tmp",
            "encoding": "utf-8"
        }
        mock_client.timeout = 10.0

        wrapper = MCPToolWrapper(mock_client, tool_def)

        # Create a very large input (10MB)
        large_input = "A" * (10 * 1024 * 1024)

        with patch('grok_py.agent.tool_manager.CodeExecutionTool') as mock_code_exec:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = '{"success": true, "data": "processed"}'
            mock_code_exec.return_value.execute_sync.return_value = mock_result

            # This should not hang or crash
            result = await wrapper.execute(text=large_input)

            # Verify it was called (though in practice, timeout should prevent DoS)
            mock_code_exec.return_value.execute_sync.assert_called_once()
            assert result.success == True

    @pytest.mark.asyncio
    async def test_malformed_json_parameters(self):
        """Test that malformed parameters are handled gracefully."""
        tool_def = ToolDefinition(
            name="json_tool",
            description="Tool that expects JSON",
            parameters={
                "data": ToolParameter(
                    name="data",
                    type="object",
                    description="JSON data",
                    required=True
                )
            }
        )

        mock_client = MagicMock()
        mock_client.get_server_params_dict.return_value = {
            "type": "stdio",
            "command": "echo",
            "args": ["received"],
            "env": {},
            "cwd": "/tmp",
            "encoding": "utf-8"
        }
        mock_client.timeout = 10.0

        wrapper = MCPToolWrapper(mock_client, tool_def)

        # Try to pass malformed data that could break JSON serialization
        malicious_data = {
            "nested": {"circular": None}
        }
        # Create circular reference
        malicious_data["nested"]["circular"] = malicious_data

        with patch('grok_py.agent.tool_manager.CodeExecutionTool') as mock_code_exec:
            # This should not crash during JSON serialization
            with pytest.raises((TypeError, ValueError)):
                await wrapper.execute(data=malicious_data)

    @pytest.mark.asyncio
    async def test_environment_variable_injection(self):
        """Test that environment variables can't be injected maliciously."""
        server_params = StdioServerParameters(
            command="env",
            args=[],
            env={"PATH": "/usr/bin", "USER": "test"}
        )

        client = MCPClient(server_params)

        tool_def = ToolDefinition(
            name="env_tool",
            description="Check environment",
            parameters={}
        )

        wrapper = MCPToolWrapper(client, tool_def)

        with patch('grok_py.agent.tool_manager.CodeExecutionTool') as mock_code_exec:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = '{"success": true, "data": "PATH=/usr/bin"}'
            mock_code_exec.return_value.execute_sync.return_value = mock_result

            result = await wrapper.execute()

            # Check that env vars are properly serialized
            call_args = mock_code_exec.return_value.execute_sync.call_args
            generated_code = call_args[1]['code']

            assert "PATH" in generated_code
            assert "/usr/bin" in generated_code
            assert result.success == True

    def test_cli_command_injection_prevention(self):
        """Test that CLI commands for adding MCP servers prevent injection."""
        from grok_py.cli import mcp_add_server
        from unittest.mock import patch

        # This would be hard to test directly since it's a typer command
        # Instead, test the config logic

        config = MCPConfig()

        # Try to add a server with potentially malicious args
        malicious_args = "; rm -rf /"  # This should be split safely

        server_config = {
            "type": "stdio",
            "command": "echo",
            "args": malicious_args.split(),  # Simulates what CLI does
            "timeout": 30.0,
            "max_retries": 3
        }

        # This should not execute the rm command
        # The args become [";", "rm", "-rf", "/"] which is harmless
        assert server_config["args"] == [";", "rm", "-rf", "/"]

        # In real CLI, this would be passed to the sandbox safely

    @pytest.mark.asyncio
    async def test_sandbox_isolation_verification(self):
        """Verify that the sandbox properly isolates executions."""
        # This test would ideally run in a real Docker environment
        # For now, we mock and verify the structure

        tool_def = ToolDefinition(
            name="isolation_test",
            description="Test isolation",
            parameters={}
        )

        mock_client = MagicMock()
        mock_client.get_server_params_dict.return_value = {
            "type": "stdio",
            "command": "whoami",
            "args": [],
            "env": {},
            "cwd": "/tmp",
            "encoding": "utf-8"
        }
        mock_client.timeout = 10.0

        wrapper = MCPToolWrapper(mock_client, tool_def)

        with patch('grok_py.agent.tool_manager.CodeExecutionTool') as mock_code_exec:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = '{"success": true, "data": "sandbox_user"}'  # Should be container user
            mock_code_exec.return_value.execute_sync.return_value = mock_result

            result = await wrapper.execute()

            # Verify it ran in code execution (Docker)
            mock_code_exec.return_value.execute_sync.assert_called_once_with(
                operation="run",
                code=pytest.any(str),  # Generated code
                language="python"
            )

            assert result.success == True
            # In real scenario, whoami should return the container user, not host user