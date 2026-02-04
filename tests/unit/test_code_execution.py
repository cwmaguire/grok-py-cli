import pytest
from unittest.mock import MagicMock

from grok_py.tools.code_execution import CodeExecutionTool
from grok_py.tools.base import ToolResult
from grok_py.tools.code_execution import Language


class TestCodeExecutionTool:
    @pytest.fixture
    def tool(self):
        return CodeExecutionTool()

    def test_execute_sync_valid_run(self, tool, mocker):
        mock_execute = mocker.patch.object(tool, '_execute_code_direct')
        mock_execute.return_value = ToolResult(success=True, data={'output': 'hello'})

        result = tool.execute_sync('run', 'print("hello")', 'python')

        assert result.success == True
        mock_execute.assert_called_once_with('print("hello")', Language.PYTHON, None, False)

    def test_execute_sync_valid_test(self, tool, mocker):
        mock_execute = mocker.patch.object(tool, '_execute_code_direct')
        mock_execute.return_value = ToolResult(success=True, data={'output': 'passed'})

        result = tool.execute_sync('test', 'assert 1 == 1', 'python', 'input')

        assert result.success == True
        mock_execute.assert_called_once_with('assert 1 == 1', Language.PYTHON, 'input', True)

    def test_execute_sync_invalid_operation(self, tool):
        result = tool.execute_sync('invalid', 'code', 'python')

        assert result.success == False
        assert 'Invalid operation' in result.error

    def test_execute_sync_empty_code(self, tool):
        result = tool.execute_sync('run', '', 'python')

        assert result.success == False
        assert 'Code cannot be empty' in result.error

    def test_execute_sync_whitespace_code(self, tool):
        result = tool.execute_sync('run', '   ', 'python')

        assert result.success == False
        assert 'Code cannot be empty' in result.error

    def test_execute_sync_unsupported_language(self, tool):
        result = tool.execute_sync('run', 'code', 'unsupported')

        assert result.success == False
        assert 'Unsupported language' in result.error

    def test_execute_sync_missing_language(self, tool):
        result = tool.execute_sync('run', 'code')

        assert result.success == False
        assert 'Language must be specified' in result.error

    def test_execute_sync_execution_error(self, tool, mocker):
        mock_execute = mocker.patch.object(tool, '_execute_code_direct')
        mock_execute.side_effect = Exception('Execution failed')

        result = tool.execute_sync('run', 'code', 'python')

        assert result.success == False
        assert 'Code execution failed' in result.error

    def test_get_supported_languages(self, tool):
        langs = tool.get_supported_languages()
        assert isinstance(langs, list)
        assert 'python' in langs
        assert 'javascript' in langs

    def test_validate_language_support_valid(self, tool):
        assert tool.validate_language_support('python') == True
        assert tool.validate_language_support('PYTHON') == True  # case insensitive

    def test_validate_language_support_invalid(self, tool):
        assert tool.validate_language_support('unsupported') == False

    def test_get_language_config_valid(self, tool):
        config = tool.get_language_config('python')
        assert config['name'] == 'Python'
        assert config['extensions'] == ['.py']
        assert config['interpreter'] == 'python3'

    def test_get_language_config_invalid(self, tool):
        config = tool.get_language_config('invalid')
        assert config == {}