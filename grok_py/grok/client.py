"""Grok API client implementation."""

import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional, Union, AsyncIterator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import httpx
from pydantic import BaseModel, Field

from grok_py.utils.settings import get_api_key, load_custom_instructions, get_conversation_history_path
from grok_py.utils.token_counter import TokenCounter


class GrokModel(str, Enum):
    """Available Grok models."""
    GROK_BETA = "grok-beta"
    GROK_VISION_BETA = "grok-vision-beta"


class MessageRole(str, Enum):
    """Message roles for chat completion."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """A chat message."""
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


@dataclass
class ToolCall:
    """A tool call from the assistant."""
    id: str
    type: str
    function: Dict[str, Any]


@dataclass
class ChatCompletion:
    """Response from chat completion."""
    id: str
    object: str
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]


class GrokAPIError(Exception):
    """Base exception for Grok API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(GrokAPIError):
    """Authentication failed."""
    pass


class RateLimitError(GrokAPIError):
    """Rate limit exceeded."""
    pass


class Conversation:
    """Represents a conversation with message history."""

    def __init__(self, conversation_id: Optional[str] = None):
        self.id = conversation_id or str(uuid.uuid4())
        self.messages: List[Message] = []
        self.created_at = asyncio.get_event_loop().time() if asyncio.get_running_loop() else None

    def add_message(self, message: Message) -> None:
        """Add a message to the conversation."""
        self.messages.append(message)

    def get_messages(self) -> List[Message]:
        """Get all messages in the conversation."""
        return self.messages.copy()

    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation to dictionary for serialization."""
        return {
            "id": self.id,
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "name": msg.name,
                    "tool_call_id": msg.tool_call_id,
                }
                for msg in self.messages
            ],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        """Create conversation from dictionary."""
        conv = cls(data["id"])
        conv.created_at = data.get("created_at")
        conv.messages = [
            Message(
                role=MessageRole(msg["role"]),
                content=msg["content"],
                name=msg.get("name"),
                tool_call_id=msg.get("tool_call_id"),
            )
            for msg in data["messages"]
        ]
        return conv


class GrokClient:
    """Client for interacting with the Grok API."""

    BASE_URL = "https://api.x.ai/v1"
    DEFAULT_TIMEOUT = 60.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ):
        """Initialize the Grok client.

        Args:
            api_key: Grok API key. If None, will try to get from environment.
            base_url: Base URL for API requests.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
        """
        self.api_key = api_key or get_api_key()
        if not self.api_key:
            raise AuthenticationError("Grok API key not found. Set GROK_API_KEY environment variable.")

        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        self.max_retries = max_retries

        # Load custom instructions
        self.custom_instructions = load_custom_instructions()

        # Initialize token counter
        self.token_counter = TokenCounter()

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

        # Current conversation
        self.current_conversation: Optional[Conversation] = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._client.aclose()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> Union[httpx.Response, AsyncIterator[bytes]]:
        """Make an HTTP request with retry logic."""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.request(
                    method=method,
                    url=endpoint,
                    json=data,
                    timeout=self.timeout,
                )

                if response.status_code == 401:
                    raise AuthenticationError("Invalid API key")
                elif response.status_code == 429:
                    raise RateLimitError("Rate limit exceeded")
                elif response.status_code >= 400:
                    raise GrokAPIError(f"API error: {response.text}", response.status_code)

                if stream:
                    return response.aiter_bytes()
                return response

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exception = e
                if attempt < self.max_retries:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise GrokAPIError(f"Request failed after {self.max_retries + 1} attempts: {str(e)}")

        raise last_exception

    async def chat_completion(
        self,
        messages: Optional[List[Message]] = None,
        model: Union[str, GrokModel] = GrokModel.GROK_BETA,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        use_conversation: bool = True,
        save_to_conversation: bool = True,
    ) -> Union[ChatCompletion, AsyncIterator[str]]:
        """Create a chat completion.

        Args:
            messages: List of messages in the conversation. If None, uses current conversation.
            model: Model to use for completion.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            stream: Whether to stream the response.
            tools: Available tools for the model to use.
            tool_choice: How to choose tools.
            use_conversation: Whether to use conversation context.
            save_to_conversation: Whether to save messages to conversation.

        Returns:
            ChatCompletion or async iterator of response chunks if streaming.
        """
        # Get messages from conversation or parameter
        if messages is None and use_conversation:
            messages = self.get_conversation_messages()
        elif messages is None:
            messages = []

        # Add custom instructions
        messages = self.get_messages_with_instructions(messages)

        request_data = {
            "model": model if isinstance(model, str) else model.value,
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    **({"name": msg.name} if msg.name else {}),
                    **({"tool_call_id": msg.tool_call_id} if msg.tool_call_id else {}),
                }
                for msg in messages
            ],
            "temperature": temperature,
            "stream": stream,
        }

        if max_tokens is not None:
            request_data["max_tokens"] = max_tokens

        if tools:
            request_data["tools"] = tools

        if tool_choice:
            request_data["tool_choice"] = tool_choice

        if stream:
            return self._stream_chat_completion(request_data, save_to_conversation)
        else:
            response = await self._make_request("POST", "/chat/completions", request_data)
            response_data = response.json()
            result = ChatCompletion(**response_data)

            # Save to conversation if requested
            if save_to_conversation and use_conversation:
                # Save user messages
                for msg in messages:
                    if msg not in self.get_conversation_messages():
                        self.add_message_to_conversation(msg)

                # Save assistant response
                if result.choices:
                    assistant_content = result.choices[0].get("message", {}).get("content", "")
                    if assistant_content:
                        assistant_msg = Message(
                            role=MessageRole.ASSISTANT,
                            content=assistant_content
                        )
                        self.add_message_to_conversation(assistant_msg)

                self.save_conversation()

            return result

    async def _stream_chat_completion(
        self,
        request_data: Dict[str, Any],
        save_to_conversation: bool = True
    ) -> AsyncIterator[str]:
        """Stream chat completion responses."""
        full_response = ""
        async for chunk in await self._make_request("POST", "/chat/completions", request_data, stream=True):
            if chunk:
                chunk_str = chunk.decode('utf-8')
                if chunk_str.startswith('data: '):
                    data = chunk_str[6:].strip()
                    if data == '[DONE]':
                        # Save to conversation when streaming is done
                        if save_to_conversation and self.current_conversation:
                            assistant_msg = Message(
                                role=MessageRole.ASSISTANT,
                                content=full_response
                            )
                            self.add_message_to_conversation(assistant_msg)
                            self.save_conversation()
                        break
                    try:
                        parsed = json.loads(data)
                        if 'choices' in parsed and parsed['choices']:
                            delta = parsed['choices'][0].get('delta', {})
                            if 'content' in delta and delta['content']:
                                content = delta['content']
                                full_response += content
                                yield content
                    except json.JSONDecodeError:
                        continue



    async def send_message(
        self,
        message: str,
        model: Union[str, GrokModel] = GrokModel.GROK_BETA,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[str, AsyncIterator[str]]:
        """Send a message and get a response.

        Args:
            message: User message.
            model: Model to use.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            stream: Whether to stream the response.
            tools: Available tools.

        Returns:
            Response content or async iterator if streaming.
        """
        # Add user message to conversation
        user_msg = Message(role=MessageRole.USER, content=message)
        self.add_message_to_conversation(user_msg)

        # Get completion
        result = await self.chat_completion(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            tools=tools,
        )

        if stream:
            return result
        else:
            # Extract content from response
            if result.choices and result.choices[0].get("message", {}).get("content"):
                return result.choices[0]["message"]["content"]
            return ""

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    def start_conversation(self, conversation_id: Optional[str] = None) -> str:
        """Start a new conversation.

        Args:
            conversation_id: Optional conversation ID.

        Returns:
            Conversation ID.
        """
        self.current_conversation = Conversation(conversation_id)
        return self.current_conversation.id

    def add_message_to_conversation(self, message: Message) -> None:
        """Add a message to the current conversation.

        Args:
            message: Message to add.
        """
        if self.current_conversation is None:
            self.start_conversation()
        self.current_conversation.add_message(message)

    def get_conversation_messages(self) -> List[Message]:
        """Get messages from the current conversation.

        Returns:
            List of messages.
        """
        if self.current_conversation is None:
            return []
        return self.current_conversation.get_messages()

    def save_conversation(self) -> None:
        """Save the current conversation to disk."""
        if self.current_conversation is None:
            return

        history_path = get_conversation_history_path()
        try:
            # Load existing conversations
            conversations = []
            if history_path.exists():
                with open(history_path, 'r') as f:
                    conversations = json.load(f)

            # Update or add current conversation
            conv_dict = self.current_conversation.to_dict()
            existing_idx = None
            for i, conv in enumerate(conversations):
                if conv["id"] == self.current_conversation.id:
                    existing_idx = i
                    break

            if existing_idx is not None:
                conversations[existing_idx] = conv_dict
            else:
                conversations.append(conv_dict)

            # Save back to file
            with open(history_path, 'w') as f:
                json.dump(conversations, f, indent=2)

        except Exception:
            # Don't fail if saving conversation fails
            pass

    def load_conversation(self, conversation_id: str) -> bool:
        """Load a conversation from disk.

        Args:
            conversation_id: ID of conversation to load.

        Returns:
            True if conversation was loaded successfully.
        """
        history_path = get_conversation_history_path()
        if not history_path.exists():
            return False

        try:
            with open(history_path, 'r') as f:
                conversations = json.load(f)

            for conv_data in conversations:
                if conv_data["id"] == conversation_id:
                    self.current_conversation = Conversation.from_dict(conv_data)
                    return True
        except Exception:
            pass

        return False

    def get_messages_with_instructions(self, user_messages: List[Message]) -> List[Message]:
        """Get messages with custom instructions prepended.

        Args:
            user_messages: User messages for the conversation.

        Returns:
            Messages with custom instructions if available.
        """
        messages = []

        # Add custom instructions as system message
        if self.custom_instructions:
            messages.append(Message(
                role=MessageRole.SYSTEM,
                content=self.custom_instructions
            ))

        # Add user messages
        messages.extend(user_messages)

        return messages

    def count_tokens(self, messages: List[Message]) -> int:
        """Count tokens in messages.

        Args:
            messages: Messages to count tokens for.

        Returns:
            Token count.
        """
        return self.token_counter.count_messages(messages)

    async def send_message(
        self,
        message: str,
        model: Union[str, GrokModel] = GrokModel.GROK_BETA,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[str, AsyncIterator[str]]:
        """Send a message and get a response.

        Args:
            message: User message.
            model: Model to use.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            stream: Whether to stream the response.
            tools: Available tools.

        Returns:
            Response content or async iterator if streaming.
        """
        # Add user message to conversation
        user_msg = Message(role=MessageRole.USER, content=message)
        self.add_message_to_conversation(user_msg)

        # Get completion
        result = await self.chat_completion(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            tools=tools,
        )

        if stream:
            return result
        else:
            # Extract content from response
            if result.choices and result.choices[0].get("message", {}).get("content"):
                return result.choices[0]["message"]["content"]
            return ""

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()