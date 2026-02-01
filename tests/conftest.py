"""Common pytest fixtures and configuration for Grok CLI tests."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

from grok_py.tools.base import ToolResult


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_files(temp_dir):
    """Create sample files in temporary directory."""
    # Copy fixture files to temp dir
    fixtures_dir = Path(__file__).parent / "fixtures"

    sample_text = temp_dir / "sample.txt"
    sample_text.write_text((fixtures_dir / "sample_text.txt").read_text())

    sample_code = temp_dir / "sample.py"
    sample_code.write_text((fixtures_dir / "sample_code.py").read_text())

    # Create additional test files
    (temp_dir / "empty.txt").write_text("")
    (temp_dir / "binary.dat").write_bytes(b"\x00\x01\x02\x03\xFF\xFE\xFD")

    # Create subdirectory
    subdir = temp_dir / "subdir"
    subdir.mkdir()
    (subdir / "nested.txt").write_text("Nested file content")

    yield temp_dir


@pytest.fixture
def mock_tool_result():
    """Create a mock ToolResult."""
    return ToolResult(
        success=True,
        data={"test": "data"},
        error=None,
        metadata={"key": "value"}
    )


@pytest.fixture
def mock_async_client():
    """Create a mock async client for testing."""
    client = AsyncMock()
    client.send_message.return_value = "Mock response"
    client.chat_completion.return_value = MagicMock(choices=[{"message": {"content": "Test"}}])
    client.add_message_to_conversation.return_value = None
    client.get_conversation_messages.return_value = []
    client.close.return_value = None
    return client


@pytest.fixture
def mock_sync_client():
    """Create a mock sync client for testing."""
    client = MagicMock()
    client.send_message.return_value = "Mock response"
    client.chat_completion.return_value = MagicMock(choices=[{"message": {"content": "Test"}}])
    client.add_message_to_conversation.return_value = None
    client.get_conversation_messages.return_value = []
    client.close.return_value = None
    return client


@pytest.fixture
def mock_tool_manager():
    """Create a mock tool manager."""
    manager = AsyncMock()
    manager.get_all_definitions.return_value = {
        "test_tool": {"name": "test_tool", "description": "Test tool"}
    }
    manager.execute_tools_parallel.return_value = [
        ToolResult(success=True, data={"result": "success"})
    ]
    manager.cleanup.return_value = None
    return manager


@pytest.fixture
def mock_docker_manager():
    """Create a mock Docker manager for code execution tests."""
    manager = MagicMock()
    manager.pull_image.return_value = True
    manager.run_container.return_value = MagicMock(
        success=True,
        stdout="Hello World\n",
        stderr="",
        exit_code=0
    )
    manager._cleanup_container.return_value = None
    return manager


@pytest.fixture
def mock_security_utils():
    """Create a mock security utils."""
    utils = MagicMock()
    utils.analyze_and_log_execution.return_value = MagicMock(risk_score=0.1, suspicious_patterns=[])
    utils.hash_code.return_value = "mock_hash"
    utils.log_execution_result.return_value = None
    return utils


@pytest.fixture
def mock_language_detector():
    """Create a mock language detector."""
    detector = MagicMock()
    detector.detect.return_value = MagicMock(value="python")
    return detector


@pytest.fixture
def mock_package_manager():
    """Create a mock package manager."""
    manager = MagicMock()
    manager.prepare_execution_environment.return_value = (
        MagicMock(image="python:3.9", command=["python", "/tmp/code.py"], extensions=[".py"]),
        MagicMock(has_dependencies=False)
    )
    manager.get_config.return_value = MagicMock(
        name="python",
        extensions=[".py"],
        image="python:3.9",
        package_manager="pip"
    )
    return manager


@pytest.fixture
def mock_web_client():
    """Create a mock web client for search tests."""
    client = MagicMock()
    client.search.return_value = {
        "results": [
            {"title": "Test", "url": "http://test.com", "content": "Test content", "score": 0.9}
        ],
        "response_time": 1.0,
        "answer": "Test answer"
    }
    return client


@pytest.fixture(autouse=True)
def mock_env():
    """Mock environment variables for tests."""
    with pytest.MonkeyPatch().context() as m:
        # Set test environment variables
        m.setenv("TAVILY_API_KEY", "test_key")
        yield m