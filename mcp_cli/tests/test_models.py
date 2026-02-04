"""
Tests for MCP CLI models
"""

import pytest
from mcp_cli.models import (
    JSONRPCRequest, JSONRPCResponse, JSONRPCNotification,
    ClientCapabilities, ServerCapabilities, ClientInfo, ServerInfo,
    InitializeRequest, InitializeResponse
)


class TestJSONRPCModels:
    """Test JSON-RPC base models"""

    def test_jsonrpc_request_creation(self):
        """Test creating a JSON-RPC request"""
        request = JSONRPCRequest(id=1, method="test.method", params={"key": "value"})
        assert request.jsonrpc == "2.0"
        assert request.id == 1
        assert request.method == "test.method"
        assert request.params == {"key": "value"}

    def test_jsonrpc_response_creation(self):
        """Test creating a JSON-RPC response"""
        response = JSONRPCResponse(id=1, result={"status": "ok"})
        assert response.jsonrpc == "2.0"
        assert response.id == 1
        assert response.result == {"status": "ok"}
        assert response.error is None

    def test_jsonrpc_notification_creation(self):
        """Test creating a JSON-RPC notification"""
        notification = JSONRPCNotification(method="test.notification", params={"key": "value"})
        assert notification.jsonrpc == "2.0"
        assert notification.method == "test.notification"
        assert notification.params == {"key": "value"}
        assert not hasattr(notification, 'id')  # Notifications don't have IDs


class TestCapabilityModels:
    """Test capability models"""

    def test_client_capabilities_creation(self):
        """Test creating client capabilities"""
        caps = ClientCapabilities()
        assert caps.experimental is None
        assert caps.logging is None
        assert caps.completions is None
        assert caps.prompts == {"listChanged": True}
        assert caps.resources == {"subscribe": True, "listChanged": True}
        assert caps.tools == {"listChanged": True}
        assert "tools" in caps.tasks["requests"]

    def test_server_capabilities_creation(self):
        """Test creating server capabilities"""
        caps = ServerCapabilities()
        assert caps.experimental is None
        assert caps.logging is None
        assert caps.prompts is None
        assert caps.resources is None
        assert caps.tools is None
        assert caps.sampling is None


class TestInfoModels:
    """Test info models"""

    def test_client_info_creation(self):
        """Test creating client info"""
        info = ClientInfo(name="test-client", version="1.0.0")
        assert info.name == "test-client"
        assert info.version == "1.0.0"
        assert info.protocolVersion == "2025-11-25"

    def test_server_info_creation(self):
        """Test creating server info"""
        info = ServerInfo(name="test-server", version="2.0.0")
        assert info.name == "test-server"
        assert info.version == "2.0.0"
        assert info.protocolVersion == "2025-11-25"


class TestInitializationModels:
    """Test initialization models"""

    def test_initialize_request_creation(self):
        """Test creating an initialize request"""
        caps = ClientCapabilities()
        info = ClientInfo(name="test-client", version="1.0")
        request = InitializeRequest(capabilities=caps, clientInfo=info)

        assert request.protocolVersion == "2025-11-25"
        assert request.capabilities == caps
        assert request.clientInfo == info

    def test_initialize_response_creation(self):
        """Test creating an initialize response"""
        server_caps = ServerCapabilities()
        server_info = ServerInfo(name="test-server", version="1.0")
        response = InitializeResponse(
            protocolVersion="2025-11-25",
            capabilities=server_caps,
            serverInfo=server_info
        )

        assert response.protocolVersion == "2025-11-25"
        assert response.capabilities == server_caps
        assert response.serverInfo == server_info
        assert response.instructions is None