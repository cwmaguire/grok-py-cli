import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from grok_py.agent.grok_agent import GrokAgent, AgentConfig, ToolCall
from grok_py.grok.client import MessageRole, ChatCompletion
from grok_py.tools.base import ToolResult


class TestAgentConfig:
    """Test AgentConfig dataclass."""

    def test_default_config(self):
        config = AgentConfig()
        assert config.model.value == "grok-beta"
        assert config.temperature == 0.7
        assert config.max_tokens is None
        assert config.max_conversation_tokens == 8000
        assert config.enable_tools == True
        assert config.auto_save_conversations == True
        assert config.debug_mode == False

    def test_custom_config(self):
        config = AgentConfig(
            temperature=0.5,
            max_tokens=100,
            enable_tools=False,
            debug_mode=True
        )
        assert config.temperature == 0.5
        assert config.max_tokens == 100
        assert config.enable_tools == False
        assert config.debug_mode == True


class TestToolCall:
    """Test ToolCall class."""

    def test_from_api_response(self):
        api_data = {
            "id": "call_123",
            "function": {
                "name": "test_tool",
                "arguments": '{"param": "value"}'
            }
        }
        tool_call = ToolCall.from_api_response(api_data)
        assert tool_call.id == "call_123"
        assert tool_call.name == "test_tool"
        assert tool_call.parameters == {"param": "value"}

    def test_to_dict(self):
        tool_call = ToolCall("call_123", "test_tool", {"param": "value"})
        result = tool_call.to_dict()
        expected = {
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "test_tool",
                "arguments": '{"param": "value"}'
            }
        }
        assert result == expected


class TestGrokAgent:
    """Test GrokAgent class."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.chat_completion = AsyncMock()
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def mock_tool_manager(self):
        manager = MagicMock()
        manager.cleanup = AsyncMock()
        return manager

    @pytest.fixture
    def agent(self, mock_client, mock_tool_manager):
        with patch('grok_py.agent.grok_agent.GrokClient', return_value=mock_client), \
             patch('grok_py.agent.grok_agent.ToolManager', return_value=mock_tool_manager):
            agent = GrokAgent()
            return agent

    def test_init_default(self, mock_client, mock_tool_manager):
        with patch('grok_py.agent.grok_agent.GrokClient', return_value=mock_client), \
             patch('grok_py.agent.grok_agent.ToolManager', return_value=mock_tool_manager):
            agent = GrokAgent()

        assert agent.config.temperature == 0.7
        assert agent.api_key is None
        assert agent.client == mock_client
        assert agent.tool_manager == mock_tool_manager
        mock_tool_manager.discover_tools.assert_called_once()
        mock_client.start_conversation.assert_called_once()

    def test_init_with_config(self, mock_client, mock_tool_manager):
        config = AgentConfig(temperature=0.5, enable_tools=False)
        with patch('grok_py.agent.grok_agent.GrokClient', return_value=mock_client), \
             patch('grok_py.agent.grok_agent.ToolManager', return_value=mock_tool_manager):
            agent = GrokAgent(config=config)

        assert agent.config.temperature == 0.5
        assert agent.config.enable_tools == False
        mock_tool_manager.discover_tools.assert_not_called()

    @pytest.mark.asyncio
    async def test_chat_without_tools(self, agent, mock_client):
        # Mock response
        mock_response = ChatCompletion(
            id="test_id",
            choices=[{
                "message": {
                    "content": "Test response",
                    "role": "assistant"
                }
            }],
            created=1234567890,
            model="grok-beta",
            object="chat.completion",
            usage={"total_tokens": 10}
        )
        mock_client.chat_completion.return_value = mock_response

        result = await agent.chat("Hello", use_tools=False)

        assert result == "Test response"
        mock_client.add_message_to_conversation.assert_called()
        mock_client.chat_completion.assert_called_once()
        args, kwargs = mock_client.chat_completion.call_args
        assert kwargs['tools'] is None

    @pytest.mark.asyncio
    async def test_chat_with_tools(self, agent, mock_client, mock_tool_manager):
        # Mock tool definitions
        mock_tool_manager.get_all_definitions.return_value = {"test_tool": {"name": "test_tool"}}

        # Mock response with tool calls
        mock_response = ChatCompletion(
            id="test_id",
            choices=[{
                "message": {
                    "content": "I'll use a tool",
                    "role": "assistant",
                    "tool_calls": [{
                        "id": "call_1",
                        "function": {
                            "name": "test_tool",
                            "arguments": '{"param": "value"}'
                        }
                    }]
                }
            }],
            created=1234567890,
            model="grok-beta",
            object="chat.completion",
            usage={"total_tokens": 20}
        )
        mock_client.chat_completion.return_value = mock_response

        # Mock tool execution
        tool_result = ToolResult(success=True, data={"result": "success"})
        agent._execute_tool_calls = AsyncMock(return_value=[tool_result])

        # Mock followup response
        followup_response = ChatCompletion(
            id="test_id_2",
            choices=[{
                "message": {
                    "content": "Tool result processed",
                    "role": "assistant"
                }
            }],
            created=1234567891,
            model="grok-beta",
            object="chat.completion",
            usage={"total_tokens": 30}
        )
        mock_client.chat_completion.side_effect = [mock_response, followup_response]

        result = await agent.chat("Use tool")

        assert result == "Tool result processed"
        agent._execute_tool_calls.assert_called_once()
        assert mock_client.chat_completion.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_tool_calls(self, agent, mock_tool_manager):
        tool_calls_data = [{
            "id": "call_1",
            "function": {
                "name": "test_tool",
                "arguments": '{"param": "value"}'
            }
        }]

        tool_result = ToolResult(success=True, data={"result": "success"})
        mock_tool_manager.execute_tools_parallel.return_value = [tool_result]

        results = await agent._execute_tool_calls(tool_calls_data)

        assert len(results) == 1
        assert results[0].success == True
        mock_tool_manager.execute_tools_parallel.assert_called_once_with([
            {"name": "test_tool", "parameters": {"param": "value"}}
        ])

    def test_get_conversation_history(self, agent, mock_client):
        mock_messages = [
            MagicMock(role=MessageRole.USER, content="Hello", timestamp="2023-01-01"),
            MagicMock(role=MessageRole.ASSISTANT, content="Hi", timestamp="2023-01-01")
        ]
        mock_client.get_conversation_messages.return_value = mock_messages

        history = agent.get_conversation_history()

        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"

    def test_clear_conversation(self, agent, mock_client):
        agent.clear_conversation()
        mock_client.start_conversation.assert_called()

    def test_save_conversation_default(self, agent, mock_client):
        mock_client.save_conversation.return_value = True
        result = agent.save_conversation()
        assert result == True
        mock_client.save_conversation.assert_called_once()

    def test_save_conversation_custom_file(self, agent, mock_client):
        with patch('builtins.open', create=True) as mock_open, \
             patch('json.dump') as mock_json_dump:
            result = agent.save_conversation("test.json")
            assert result == True
            mock_open.assert_called_once_with("test.json", 'w')

    def test_load_conversation(self, agent, mock_client):
        mock_client.load_conversation.return_value = True
        result = agent.load_conversation("conv_123")
        assert result == True
        mock_client.load_conversation.assert_called_once_with("conv_123")

    @pytest.mark.asyncio
    async def test_context_manager(self, agent, mock_client, mock_tool_manager):
        async with agent:
            pass

        mock_client.close.assert_called_once()
        mock_tool_manager.cleanup.assert_called_once()
        mock_client.save_conversation.assert_called_once()

    def test_get_token_usage(self, agent, mock_client):
        # Mock the client methods
        mock_messages = [MagicMock()]
        mock_client.get_conversation_messages.return_value = mock_messages
        with patch.object(agent, 'token_counter') as mock_counter:
            mock_counter.count_messages.return_value = 100
            usage = agent.get_token_usage()
            expected = {
                "total_tokens": 100,
                "messages_count": 1,
                "max_allowed": 8000,
                "remaining": 7900
            }
            assert usage == expected