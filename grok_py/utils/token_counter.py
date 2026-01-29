"""Token counting utilities using tiktoken."""

import tiktoken
from typing import List, Union

from grok_py.grok.client import Message


class TokenCounter:
    """Token counter for Grok models using tiktoken."""

    def __init__(self, model: str = "grok-beta"):
        """Initialize token counter.

        Args:
            model: Model name for encoding selection.
        """
        # Map Grok models to tiktoken encodings
        # Since Grok uses similar tokenization to GPT models, we'll use cl100k_base
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except:
            # Fallback if tiktoken data not available
            self.encoding = None

    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string.

        Args:
            text: Text to count tokens for.

        Returns:
            Number of tokens.
        """
        if self.encoding is None:
            # Fallback: rough estimation (4 chars per token)
            return len(text) // 4

        return len(self.encoding.encode(text))

    def count_messages(self, messages: List[Message]) -> int:
        """Count tokens in a list of messages.

        Args:
            messages: List of messages.

        Returns:
            Total token count including formatting.
        """
        total_tokens = 0

        for message in messages:
            # Count role, content, and formatting tokens
            total_tokens += 4  # Every message follows <|start|>{role/name}\n{content}<|end|>\n

            # Role
            total_tokens += self.count_tokens(message.role.value)

            # Content
            total_tokens += self.count_tokens(message.content)

            # Name (if present)
            if message.name:
                total_tokens += self.count_tokens(message.name) - 1  # -1 for the space saved

            # Tool call ID (if present)
            if message.tool_call_id:
                total_tokens += self.count_tokens(message.tool_call_id)

        # Add tokens for the overall format
        total_tokens += 3  # Every reply is primed with <|start|>assistant<|message|>

        return total_tokens

    def estimate_max_tokens(self, messages: List[Message], max_completion_tokens: int = 4096) -> int:
        """Estimate maximum tokens available for completion.

        Args:
            messages: Conversation messages.
            max_completion_tokens: Maximum tokens for completion.

        Returns:
            Estimated tokens available for completion.
        """
        conversation_tokens = self.count_messages(messages)
        return max_completion_tokens - conversation_tokens