"""
MCP (Model Context Protocol) SSE Handler

Handles Server-Sent Events for receiving notifications from MCP server.
"""

import logging
import threading
import time
from typing import Callable, Optional, Dict, Any
import sseclient
import requests
from .models import JSONRPCNotification

logger = logging.getLogger('mcp_cli.sse')


class SSEHandler:
    """Handler for Server-Sent Events notifications"""

    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._callbacks: Dict[str, Callable[[JSONRPCNotification], None]] = {}

    def add_callback(self, method: str, callback: Callable[[JSONRPCNotification], None]) -> None:
        """
        Add a callback for a specific notification method

        Args:
            method: Notification method name
            callback: Function to call when notification is received
        """
        self._callbacks[method] = callback

    def remove_callback(self, method: str) -> None:
        """Remove callback for a method"""
        self._callbacks.pop(method, None)

    def start(self) -> None:
        """Start listening for SSE notifications in background thread"""
        if self._thread and self._thread.is_alive():
            logger.debug("SSE handler already running")
            return  # Already running

        logger.info("Starting SSE notification listener")
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop listening for notifications"""
        logger.info("Stopping SSE notification listener")
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            logger.debug("SSE thread joined")

    def _listen_loop(self) -> None:
        """Main SSE listening loop"""
        while self._running:
            try:
                # Connect to SSE endpoint
                response = requests.get(
                    f"{self.server_url}/mcp",
                    stream=True,
                    headers={"Accept": "text/event-stream"}
                )
                response.raise_for_status()

                client = sseclient.SSEClient(response)

                for event in client.events():
                    if not self._running:
                        break

                    if event.event == 'message' and event.data:
                        try:
                            # Parse JSON-RPC notification
                            notification_data = JSONRPCNotification.parse_raw(event.data)
                            logger.debug(f"Received notification: {notification_data.method}")
                            self._handle_notification(notification_data)
                        except Exception as e:
                            logger.error(f"Error parsing notification: {e}")
                            print(f"Error parsing notification: {e}")

            except requests.RequestException as e:
                logger.error(f"SSE connection error: {e}")
                print(f"SSE connection error: {e}")
                if self._running:
                    logger.debug("Retrying SSE connection in 5 seconds")
                    time.sleep(5)  # Retry after delay
            except Exception as e:
                logger.error(f"SSE handler error: {e}", exc_info=True)
                print(f"SSE handler error: {e}")
                if self._running:
                    time.sleep(5)

    def _handle_notification(self, notification: JSONRPCNotification) -> None:
        """Handle incoming notification by calling appropriate callback"""
        callback = self._callbacks.get(notification.method)
        if callback:
            try:
                logger.debug(f"Calling callback for notification: {notification.method}")
                callback(notification)
            except Exception as e:
                logger.error(f"Error in notification callback for {notification.method}: {e}")
                print(f"Error in notification callback for {notification.method}: {e}")
        else:
            logger.warning(f"No callback registered for notification method: {notification.method}")
            print(f"No callback registered for notification method: {notification.method}")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()