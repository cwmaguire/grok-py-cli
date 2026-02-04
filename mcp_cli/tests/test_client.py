"""
Tests for MCP CLI client
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from mcp_cli.client import MCPClient
from mcp_cli.models import JSONRPCResponse, MCPError


class TestMCPClient:
    """Test MCP client functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        self.client = MCPClient("http://test-server:8000")

    def test_client_initialization(self):
        """Test client initialization"""
        assert self.client.server_url == "http://test-server:8000/"
        assert self.client.session_id is None
        assert self.client._request_id == 0

    def test_request_id_generation(self):
        """Test request ID generation"""
        assert self.client._get_next_request_id() == 1
        assert self.client._get_next_request_id() == 2
        assert self.client._get_next_request_id() == 3

    @patch('mcp_cli.client.requests.Session.post')
    def test_send_request_success(self, mock_post):
        """Test successful request sending"""
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"status": "ok"}
        }
        mock_post.return_value = mock_response

        result = self.client.send_request("test.method", {"param": "value"})

        assert result == {"status": "ok"}
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["method"] == "test.method"
        assert call_args[1]["json"]["params"] == {"param": "value"}

    @patch('mcp_cli.client.requests.Session.post')
    def test_send_request_jsonrpc_error(self, mock_post):
        """Test JSON-RPC error handling"""
        # Mock response with error
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32601, "message": "Method not found"}
        }
        mock_post.return_value = mock_response

        with pytest.raises(MCPError) as exc_info:
            self.client.send_request("invalid.method")

        assert exc_info.value.code == -32601
        assert exc_info.value.message == "Method not found"

    @patch('mcp_cli.client.requests.Session.post')
    def test_send_request_http_error(self, mock_post):
        """Test HTTP error handling"""
        # Mock HTTP error
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_post.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            self.client.send_request("test.method")

    @patch('mcp_cli.client.requests.Session.post')
    def test_initialize_success(self, mock_post):
        """Test successful initialization"""
        # Mock successful initialize response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2025-11-25",
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {"subscribe": True}
                },
                "serverInfo": {
                    "name": "Test Server",
                    "version": "1.0.0"
                }
            }
        }
        mock_post.return_value = mock_response

        result = self.client.initialize("test-client", "1.0")

        assert result.serverInfo.name == "Test Server"
        assert result.serverInfo.version == "1.0.0"
        assert result.capabilities.tools is not None
        assert result.capabilities.resources is not None

    def test_close(self):
        """Test client close method"""
        with patch.object(self.client.session, 'close') as mock_close:
            self.client.close()
            mock_close.assert_called_once()