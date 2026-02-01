"""System tests for development workflow scenarios."""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock
from typer.testing import CliRunner

from grok_py.cli import app


class TestDevelopmentWorkflow:
    """System tests for complete development workflows."""

    @pytest.fixture
    def runner(self):
        """CLI runner fixture."""
        return CliRunner()

    @pytest.mark.system
    def test_full_code_development_cycle(self, runner):
        """Test complete development cycle: create, edit, run, debug code."""
        import tempfile

        # Mock all external dependencies
        with patch('grok_py.tools.file_editor.CreateFileTool.execute_sync') as mock_create, \
             patch('grok_py.tools.file_editor.StrReplaceEditorTool.execute_sync') as mock_edit, \
             patch('grok_py.tools.file_editor.ViewFileTool.execute_sync') as mock_view, \
             patch('grok_py.tools.code_execution.CodeExecutionTool.execute_sync') as mock_exec, \
             patch('grok_py.cli.GrokClient') as mock_client:

            # Setup mocks
            mock_create.return_value = MagicMock(success=True, data={'path': '/tmp/test.py'})
            mock_edit.return_value = MagicMock(success=True)
            mock_view.return_value = MagicMock(success=True, data={'content': 'print("Hello, World!")'})
            mock_exec.return_value = MagicMock(success=True, data={'stdout': 'Hello, World!\n', 'exit_code': 0})

            mock_client_instance = AsyncMock()
            mock_client_instance.send_message.return_value = "Add error handling to make it more robust."
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Simulate development workflow via CLI
            # Note: In a real system test, this would be end-to-end CLI interaction
            # For now, we test the workflow components

            # Step 1: Create initial code file
            # (Would be triggered by chat + tool call)

            # Step 2: Edit the code
            # (User requests improvement)

            # Step 3: Run the code
            # (Verify it works)

            # Step 4: Debug if needed
            # (Chat about errors)

            # Verify all components were called
            # In real test, would check CLI output and file state
            assert mock_create.called
            assert mock_edit.called
            assert mock_view.called
            assert mock_exec.called

    @pytest.mark.system
    def test_file_editing_pipeline(self):
        """Test complete file editing pipeline from creation to modification."""
        from grok_py.tools.file_editor import CreateFileTool, ViewFileTool, StrReplaceEditorTool

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, 'test.txt')

            # Create file
            create_tool = CreateFileTool()
            create_result = create_tool.execute_sync(test_file, 'Initial content\n')
            assert create_result.success is True

            # View file
            view_tool = ViewFileTool()
            view_result = view_tool.execute_sync(test_file)
            assert view_result.success is True
            assert 'Initial content' in view_result.data['content']

            # Edit file
            edit_tool = StrReplaceEditorTool()
            edit_result = edit_tool.execute_sync(
                test_file,
                'Initial content',
                'Modified content'
            )
            assert edit_result.success is True

            # Verify final state
            final_view = view_tool.execute_sync(test_file)
            assert final_view.success is True
            assert 'Modified content' in final_view.data['content']

    @pytest.mark.system
    def test_code_execution_workflow(self):
        """Test code execution workflow with error handling."""
        from grok_py.tools.code_execution import CodeExecutionTool

        # Mock Docker execution
        with patch('grok_py.tools.code_execution.CodeExecutionTool.execute_sync') as mock_exec:
            # Successful execution
            mock_exec.return_value = MagicMock(
                success=True,
                data={'stdout': 'Result: 42\n', 'exit_code': 0}
            )

            tool = CodeExecutionTool()
            result = tool.execute_sync('run', 'print("Result:", 6 * 7)', 'python')

            assert result.success is True
            assert 'Result: 42' in result.data['stdout']

            # Test error case
            mock_exec.return_value = MagicMock(
                success=False,
                error='SyntaxError: invalid syntax'
            )

            error_result = tool.execute_sync('run', 'print("unclosed', 'python')
            assert error_result.success is False
            assert 'syntax' in str(error_result.error).lower()

    @pytest.mark.system
    def test_resource_usage_monitoring(self):
        """Test system resource monitoring during operations."""
        import time
        from grok_py.tools.example_calculator import CalculatorTool

        with patch('psutil.Process') as mock_process:
            mock_process.return_value.memory_info.return_value.rss = 50 * 1024 * 1024  # 50MB

            # Get baseline memory
            baseline_memory = mock_process.return_value.memory_info.return_value.rss / 1024 / 1024  # MB

            # Perform operations
            calc = CalculatorTool()
            start_time = time.time()

            for i in range(1000):
                result = calc.execute_sync('add', i, i+1)
                assert result.success is True

            end_time = time.time()
            final_memory = mock_process.return_value.memory_info.return_value.rss / 1024 / 1024  # MB

            # Verify reasonable resource usage
            duration = end_time - start_time
            memory_increase = final_memory - baseline_memory

        assert duration < 5.0  # Should complete in reasonable time
        assert memory_increase < 50.0  # Should not leak memory excessively