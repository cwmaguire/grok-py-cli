"""
MCP (Model Context Protocol) HTTP Client

Handles JSON-RPC 2.0 communication over HTTP with session management.
"""

import logging
import requests
from typing import Optional, Dict, Any, Union
import json
from .models import (
    JSONRPCRequest, JSONRPCResponse, JSONRPCNotification,
    InitializeRequest, InitializeResponse, ClientInfo, ClientCapabilities,
    MCPError
)

logger = logging.getLogger('mcp_cli.client')


class MCPClient:
    """HTTP client for MCP server communication"""

    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
        self.session = requests.Session()
        self.session_id: Optional[str] = None
        self._request_id = 0

    def _get_next_request_id(self) -> int:
        """Generate next request ID"""
        self._request_id += 1
        return self._request_id

    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a JSON-RPC request and return the result

        Args:
            method: RPC method name
            params: Method parameters

        Returns:
            Parsed result dictionary

        Raises:
            MCPError: For JSON-RPC errors
            requests.HTTPError: For HTTP errors
        """
        request_id = self._get_next_request_id()
        request = JSONRPCRequest(
            id=request_id,
            method=method,
            params=params
        )

        logger.debug(f"Sending JSON-RPC request: method={method}, id={request_id}")

        try:
            response = self.session.post(
                f"{self.server_url}/mcp",
                json=request.dict(),
                headers={"Content-Type": "application/json"}
            )

            response.raise_for_status()

            rpc_response = JSONRPCResponse(**response.json())

            if rpc_response.error:
                logger.error(f"JSON-RPC error for request {request_id}: {rpc_response.error}")
                raise MCPError(**rpc_response.error)

            logger.debug(f"JSON-RPC request {request_id} completed successfully")
            return rpc_response.result or {}

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed for method {method}: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid JSON response for request {request_id}: {e}")
            raise

    def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """
        Send a JSON-RPC notification (no response expected)

        Args:
            method: RPC method name
            params: Method parameters
        """
        notification = JSONRPCNotification(
            method=method,
            params=params
        )

        response = self.session.post(
            f"{self.server_url}/mcp",
            json=notification.dict(),
            headers={"Content-Type": "application/json"}
        )

        response.raise_for_status()

    def initialize(self, client_name: str = "mcp-cli", client_version: str = "1.0") -> InitializeResponse:
        """
        Perform MCP initialization handshake

        Args:
            client_name: Client application name
            client_version: Client version string

        Returns:
            InitializeResponse with server capabilities
        """
        logger.info(f"Initializing MCP client: {client_name} v{client_version}")
        init_params = InitializeRequest(
            capabilities=ClientCapabilities(),
            clientInfo=ClientInfo(
                name=client_name,
                version=client_version
            )
        )

        # Create full request
        request = JSONRPCRequest(
            id=self._get_next_request_id(),
            method="initialize",
            params=init_params.dict()
        )

        response = self.session.post(
            f"{self.server_url}/mcp",
            json=request.dict(),
            headers={"Content-Type": "application/json"}
        )

        response.raise_for_status()

        rpc_response = JSONRPCResponse(**response.json())

        if rpc_response.error:
            raise MCPError(**rpc_response.error)

        init_result = InitializeResponse(**rpc_response.result)

        # Store session ID if provided (though spec may not require it)
        # Some implementations might include it in result
        self.session_id = getattr(init_result, 'sessionId', None)

        logger.info(f"MCP initialization successful. Server: {init_result.serverInfo.name}")
        return init_result

    def close(self):
        """Close the HTTP session"""
        self.session.close()