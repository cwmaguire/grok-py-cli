"""Unit tests for token counter utility."""

import pytest
from unittest.mock import patch, MagicMock

from grok_py.utils.token_counter import TokenCounter


class TestTokenCounter:
    """Test token counting functionality."""

    def test_count_tokens_basic_text(self):
        """Test basic token counting."""
        counter = TokenCounter()
        text = "Hello world"
        count = counter.count_tokens(text)
        assert isinstance(count, int)
        assert count > 0

    def test_count_tokens_empty_string(self):
        """Test token counting for empty string."""
        counter = TokenCounter()
        count = counter.count_tokens("")
        assert count == 0

    def test_count_tokens_with_encoding(self):
        """Test token counting with specific encoding."""
        counter = TokenCounter()
        text = "This is a test message"
        count = counter.count_tokens(text, encoding="cl100k_base")
        assert isinstance(count, int)
        assert count > 0

    def test_estimate_cost(self):
        """Test cost estimation."""
        counter = TokenCounter()
        text = "This is a sample text for cost estimation"
        cost = counter.estimate_cost(text, model="gpt-3.5-turbo")
        assert isinstance(cost, float)
        assert cost >= 0

    def test_estimate_cost_different_models(self):
        """Test cost estimation for different models."""
        counter = TokenCounter()
        text = "Sample text"

        # Test different models
        gpt4_cost = counter.estimate_cost(text, model="gpt-4")
        gpt35_cost = counter.estimate_cost(text, model="gpt-3.5-turbo")

        assert gpt4_cost > gpt35_cost  # GPT-4 should be more expensive

    def test_token_limit_check(self):
        """Test token limit checking."""
        counter = TokenCounter()
        short_text = "Hello"
        long_text = "This is a very long text that exceeds typical token limits " * 100

        assert counter.is_within_limit(short_text, 1000)
        assert not counter.is_within_limit(long_text, 100)

    @patch('grok_py.utils.token_counter.tiktoken')
    def test_fallback_encoding(self, mock_tiktoken):
        """Test fallback when tiktoken encoding fails."""
        mock_tiktoken.get_encoding.side_effect = Exception("Encoding not found")

        counter = TokenCounter()
        text = "Test text"
        count = counter.count_tokens(text)

        # Should fall back to character-based estimation
        assert isinstance(count, int)

    def test_context_window_info(self):
        """Test getting context window information."""
        counter = TokenCounter()
        info = counter.get_context_window("gpt-4")

        assert "max_tokens" in info
        assert "model" in info
        assert info["model"] == "gpt-4"

    def test_unsupported_model_fallback(self):
        """Test handling of unsupported models."""
        counter = TokenCounter()
        cost = counter.estimate_cost("text", model="unsupported-model")

        # Should not crash and return some cost
        assert isinstance(cost, float)