"""Main Grok agent class for managing conversations and tool orchestration."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from grok_py.grok.client import GrokClient, GrokModel, Message, MessageRole, ChatCompletion
from grok_py.agent.tool_manager import ToolManager
from grok_py.tools.base import ToolResult
from grok_py.utils.token_counter import TokenCounter


logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for the Grok agent."""
    model: GrokModel = GrokModel.GROK_CODE_FAST_1
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    max_conversation_tokens: int = 8000
    enable_tools: bool = True
    auto_save_conversations: bool = True
    debug_mode: bool = False


class ToolCall:
    """Represents a tool call from the assistant."""

    def __init__(self, call_id: str, tool_name: str, parameters: Dict[str, Any]):
        self.id = call_id
        self.name = tool_name
        self.parameters = parameters

    @classmethod
    def from_api_response(cls, tool_call_data: Dict[str, Any]) -> "ToolCall":
        """Create ToolCall from API response data."""
        function = tool_call_data.get("function", {})
        return cls(
            call_id=tool_call_data.get("id", ""),
            tool_name=function.get("name", ""),
            parameters=json.loads(function.get("arguments", "{}"))
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": json.dumps(self.parameters)
            }
        }


class GrokAgent:
    """Main agent class for coordinating Grok conversations and tool usage."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[AgentConfig] = None,
        tool_manager: Optional[ToolManager] = None
    ):
        """Initialize the Grok agent.

        Args:
            api_key: Grok API key (optional, will use environment if not provided)
            config: Agent configuration
            tool_manager: Tool manager instance (optional, will create if not provided)
        """
        self.config = config or AgentConfig()
        self.api_key = api_key

        # Initialize components
        self.client = GrokClient(
            api_key=self.api_key,
            timeout=60.0,  # Longer timeout for complex operations
            max_retries=3
        )

        self.tool_manager = tool_manager or ToolManager()
        self.token_counter = TokenCounter()

        # Discover and register tools
        if self.config.enable_tools:
            self.tool_manager.discover_tools()

        # Start conversation
        self.client.start_conversation()

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        if self.config.debug_mode:
            self.logger.setLevel(logging.DEBUG)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.close()
        if self.tool_manager:
            await self.tool_manager.cleanup()

        if self.config.auto_save_conversations:
            self.client.save_conversation()

    async def chat(
        self,
        message: str,
        use_tools: Optional[bool] = None,
        **kwargs
    ) -> str:
        """Send a message and get a response, potentially using tools.

        Args:
            message: User message
            use_tools: Whether to enable tool usage (defaults to config setting)
            **kwargs: Additional parameters for the API call

        Returns:
            Assistant response
        """
        if use_tools is None:
            use_tools = self.config.enable_tools

        # Add user message to conversation
        user_msg = Message(role=MessageRole.USER, content=message)
        self.client.add_message_to_conversation(user_msg)

        # Prepare tool definitions if tools are enabled
        tools = None
        if use_tools and self.tool_manager:
            tools = list(self.tool_manager.get_all_definitions().values())

        # Get response from Grok
        response = await self.client.chat_completion(
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            tools=tools,
            **kwargs
        )

        if not isinstance(response, ChatCompletion):
            # Handle streaming response differently
            return await self._handle_streaming_response(response)

        return await self._handle_chat_completion(response)

    async def _handle_chat_completion(self, response: ChatCompletion) -> str:
        """Handle a chat completion response, including tool calls.

        Args:
            response: Chat completion response

        Returns:
            Final response content
        """
        if not response.choices:
            return "No response generated."

        choice = response.choices[0]
        message_data = choice.get("message", {})
        content = message_data.get("content", "")
        tool_calls_data = message_data.get("tool_calls", [])

        # If there are tool calls, execute them
        if tool_calls_data:
            tool_results = await self._execute_tool_calls(tool_calls_data)

            # Add tool results to conversation
            for tool_call_data, tool_result in zip(tool_calls_data, tool_results):
                # Add assistant message with tool calls
                assistant_msg = Message(
                    role=MessageRole.ASSISTANT,
                    content=content,
                    tool_call_id=tool_call_data.get("id")
                )
                self.client.add_message_to_conversation(assistant_msg)

                # Add tool result message
                tool_msg = Message(
                    role=MessageRole.TOOL,
                    content=json.dumps({
                        "success": tool_result.success,
                        "data": tool_result.data,
                        "error": tool_result.error
                    }),
                    tool_call_id=tool_call_data.get("id")
                )
                self.client.add_message_to_conversation(tool_msg)

            # Get follow-up response after tool execution
            followup_response = await self.client.chat_completion(
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )

            if isinstance(followup_response, ChatCompletion) and followup_response.choices:
                followup_content = followup_response.choices[0].get("message", {}).get("content", "")
                if followup_content:
                    content = followup_content

        # Add final assistant response to conversation
        if content:
            final_msg = Message(role=MessageRole.ASSISTANT, content=content)
            self.client.add_message_to_conversation(final_msg)

        return content

    async def _handle_streaming_response(self, stream) -> str:
        """Handle streaming response.

        Args:
            stream: Streaming response iterator

        Returns:
            Complete response content
        """
        full_content = ""
        async for chunk in stream:
            full_content += chunk
            if self.config.debug_mode:
                print(f"\r{full_content}", end="", flush=True)

        if self.config.debug_mode:
            print()  # New line after streaming

        # Add to conversation
        if full_content:
            msg = Message(role=MessageRole.ASSISTANT, content=full_content)
            self.client.add_message_to_conversation(msg)

        return full_content

    async def _execute_tool_calls(self, tool_calls_data: List[Dict[str, Any]]) -> List[ToolResult]:
        """Execute tool calls.

        Args:
            tool_calls_data: List of tool call data from API

        Returns:
            List of tool results
        """
        tool_calls = []
        for call_data in tool_calls_data:
            tool_call = ToolCall.from_api_response(call_data)
            tool_calls.append({
                "name": tool_call.name,
                "parameters": tool_call.parameters
            })

        self.logger.debug(f"Executing {len(tool_calls)} tool calls")

        # Execute tools (can be parallel if tool manager supports it)
        results = await self.tool_manager.execute_tools_parallel(tool_calls)

        # Log results
        for i, result in enumerate(results):
            tool_name = tool_calls[i]["name"]
            if result.success:
                self.logger.info(f"Tool '{tool_name}' executed successfully")
            else:
                self.logger.error(f"Tool '{tool_name}' failed: {result.error}")

        return results

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history.

        Returns:
            List of conversation messages
        """
        messages = self.client.get_conversation_messages()
        return [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": getattr(msg, 'timestamp', None)
            }
            for msg in messages
        ]

    def clear_conversation(self) -> None:
        """Clear the current conversation."""
        self.client.start_conversation()
        self.logger.info("Conversation cleared")

    def save_conversation(self, filename: Optional[str] = None) -> bool:
        """Save the current conversation.

        Args:
            filename: Optional filename to save to

        Returns:
            True if saved successfully
        """
        try:
            if filename:
                # Save to specific file
                conversation_data = {
                    "conversation_id": self.client.current_conversation.id,
                    "messages": [
                        {
                            "role": msg.role.value,
                            "content": msg.content,
                            "name": msg.name,
                            "tool_call_id": msg.tool_call_id
                        }
                        for msg in self.client.get_conversation_messages()
                    ]
                }
                with open(filename, 'w') as f:
                    json.dump(conversation_data, f, indent=2)
            else:
                # Use default save method
                self.client.save_conversation()

            self.logger.info(f"Conversation saved{' to ' + filename if filename else ''}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save conversation: {e}")
            return False

    def load_conversation(self, conversation_id: str) -> bool:
        """Load a conversation by ID.

        Args:
            conversation_id: Conversation ID to load

        Returns:
            True if loaded successfully
        """
        success = self.client.load_conversation(conversation_id)
        if success:
            self.logger.info(f"Conversation '{conversation_id}' loaded")
        else:
            self.logger.warning(f"Failed to load conversation '{conversation_id}'")
        return success

    def get_token_usage(self) -> Dict[str, int]:
        """Get token usage statistics.

        Returns:
            Dictionary with token usage info
        """
        messages = self.client.get_conversation_messages()
        total_tokens = self.token_counter.count_messages(messages)

        return {
            "total_tokens": total_tokens,
            "messages_count": len(messages),
            "max_allowed": self.config.max_conversation_tokens,
            "remaining": max(0, self.config.max_conversation_tokens - total_tokens)
        }

    def set_config(self, **kwargs) -> None:
        """Update agent configuration.

        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                self.logger.info(f"Configuration updated: {key} = {value}")
            else:
                self.logger.warning(f"Unknown configuration parameter: {key}")

    def get_available_tools(self) -> List[str]:
        """Get list of available tools.

        Returns:
            List of tool names
        """
        if self.tool_manager:
            return self.tool_manager.list_tools()
        return []

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on agent and tools.

        Returns:
            Health status dictionary
        """
        health = {
            "agent": "healthy",
            "client": "unknown",
            "tools": "unknown",
            "conversation": "active" if self.client.current_conversation else "inactive"
        }

        # Check client connectivity (simple ping)
        try:
            # This is a placeholder - in real implementation, you'd do a simple API call
            health["client"] = "healthy"
        except Exception as e:
            health["client"] = f"unhealthy: {str(e)}"

        # Check tools
        if self.tool_manager:
            try:
                tool_health = await self.tool_manager.health_check()
                healthy_tools = sum(1 for t in tool_health.values() if t["status"] == "healthy")
                total_tools = len(tool_health)
                health["tools"] = f"{healthy_tools}/{total_tools} healthy"
            except Exception as e:
                health["tools"] = f"error: {str(e)}"
        else:
            health["tools"] = "no tool manager"

        return health