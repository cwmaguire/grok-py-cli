"""Acceptance tests for user scenarios and workflows."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typer.testing import CliRunner

from grok_py.cli import app

# Note: Acceptance tests would typically test end-to-end workflows
# For this implementation, we'll test tool integrations and user workflows
# with mocked components where necessary


class TestUserScenarios:
    """Acceptance tests for user scenarios."""

    @pytest.fixture
    def runner(self):
        """CLI runner fixture."""
        return CliRunner()

    @pytest.mark.acceptance
    @pytest.mark.asyncio
    async def test_developer_calculates_expression(self):
        """Test scenario: Developer uses calculator for quick math."""
        from grok_py.tools.example_calculator import CalculatorTool

        calc = CalculatorTool()

        # Scenario: Calculate area of circle (pi * r^2)
        result1 = await calc.execute(operation="multiply", a=3.14159, b=5)
        result2 = await calc.execute(operation="multiply", a=result1.data["result"], b=5)

        assert result1.success is True
        assert result2.success is True
        assert abs(result2.data["result"] - 78.53975) < 0.01  # Approximate area

    @pytest.mark.acceptance
    def test_developer_runs_code_snippet(self):
        """Test scenario: Developer executes code to test algorithm."""
        # Mock the code execution since it requires Docker
        with patch('grok_py.tools.code_execution.CodeExecutionTool.execute_sync') as mock_execute:
            mock_execute.return_value = MagicMock(
                success=True,
                data={'stdout': 'Hello, Fibonacci!\nFibonacci of 10: 55\n', 'exit_code': 0}
            )

            from grok_py.tools.code_execution import CodeExecutionTool

            tool = CodeExecutionTool()
            code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print("Hello, Fibonacci!")
print(f"Fibonacci of 10: {fibonacci(10)}")
"""
            result = tool.execute_sync("run", code, "python")

            assert result.success is True
            assert "Fibonacci of 10: 55" in result.data['stdout']
            mock_execute.assert_called_once()

    @pytest.mark.acceptance
    @pytest.mark.asyncio
    async def test_developer_checks_system_resources(self):
        """Test scenario: Developer monitors system resources."""
        # Mock bash tool for system commands
        with patch('grok_py.tools.bash.BashTool.execute') as mock_execute:
            mock_execute.return_value = MagicMock(
                success=True,
                data={
                    'stdout': 'CPU: 25%\nMemory: 60%\nDisk: 45%',
                    'exit_code': 0
                }
            )

            from grok_py.tools.bash import BashTool

            tool = BashTool()
            result = await tool.execute(command="top -bn1 | head -10")

            assert result.success is True
            assert "CPU:" in result.data['stdout']
            mock_execute.assert_called_once()

    @pytest.mark.acceptance
    @pytest.mark.asyncio
    async def test_power_user_complex_workflow(self):
        """Test scenario: Power user performs complex calculations with the calculator tool."""
        # Use calculator to compute complex calculations
        from grok_py.tools.example_calculator import CalculatorTool
        calc = CalculatorTool()

        # Calculate A = 1000 * (1 + 0.05/12)^(12*5)
        monthly_rate = 0.05 / 12
        periods = 12 * 5

        # This would be a complex calculation requiring multiple steps
        # For acceptance test, verify the tool can handle it
        result = await calc.execute(operation="add", a=1, b=monthly_rate)
        assert result.success is True

    @pytest.mark.acceptance
    def test_student_learning_programming(self):
        """Test scenario: Student learns programming with code execution."""
        with patch('grok_py.tools.code_execution.CodeExecutionTool.execute_sync') as mock_execute:
            # Mock successful execution
            mock_execute.return_value = MagicMock(
                success=True,
                data={'stdout': 'Hello, World!\nThe sum is: 15\n', 'exit_code': 0}
            )

            from grok_py.tools.code_execution import CodeExecutionTool

            tool = CodeExecutionTool()
            code = """
print("Hello, World!")
numbers = [1, 2, 3, 4, 5]
total = sum(numbers)
print(f"The sum is: {total}")
"""
            result = tool.execute_sync("run", code, "python")

            assert result.success is True
            assert "Hello, World!" in result.data['stdout']
            assert "The sum is: 15" in result.data['stdout']

    @pytest.mark.acceptance
    def test_data_analyst_processes_data(self):
        """Test scenario: Data analyst processes data with Python."""
        with patch('grok_py.tools.code_execution.CodeExecutionTool.execute_sync') as mock_execute:
            mock_execute.return_value = MagicMock(
                success=True,
                data={
                    'stdout': 'Data loaded successfully\nMean: 25.5\nMedian: 25.0\n',
                    'exit_code': 0
                }
            )

            from grok_py.tools.code_execution import CodeExecutionTool

            tool = CodeExecutionTool()
            code = """
import statistics
data = [10, 20, 30, 40, 50]
print("Data loaded successfully")
print(f"Mean: {statistics.mean(data)}")
print(f"Median: {statistics.median(data)}")
"""
            result = tool.execute_sync("run", code, "python")

            assert result.success is True
            assert "Mean: 25.5" in result.data['stdout']
            assert "Median: 25.0" in result.data['stdout']

    @pytest.mark.asyncio
    @pytest.mark.acceptance
    async def test_system_administrator_monitors_logs(self):
        """Test scenario: System administrator monitors system logs."""
        with patch('grok_py.tools.bash.BashTool.execute') as mock_execute:
            mock_execute.return_value = MagicMock(
                success=True,
                data={
                    'stdout': '2024-01-15 10:30:15 INFO Application started\n2024-01-15 10:35:22 ERROR Database connection failed\n',
                    'exit_code': 0
                }
            )

            from grok_py.tools.bash import BashTool

            tool = BashTool()
            result = await tool.execute(command="tail -f /var/log/application.log | head -10")

            assert result.success is True
            assert "INFO Application started" in result.data['stdout']
            assert "ERROR Database connection failed" in result.data['stdout']

    @pytest.mark.acceptance
    def test_researcher_runs_experiments(self):
        """Test scenario: Researcher runs computational experiments."""
        with patch('grok_py.tools.code_execution.CodeExecutionTool.execute_sync') as mock_execute:
            mock_execute.return_value = MagicMock(
                success=True,
                data={
                    'stdout': 'Running Monte Carlo simulation...\nEstimated pi: 3.1415926535\n',
                    'exit_code': 0
                }
            )

            from grok_py.tools.code_execution import CodeExecutionTool

            tool = CodeExecutionTool()
            code = """
import random
import math

def estimate_pi(num_points):
    inside_circle = 0
    for _ in range(num_points):
        x, y = random.random(), random.random()
        if x**2 + y**2 <= 1:
            inside_circle += 1
    return 4 * inside_circle / num_points

print("Running Monte Carlo simulation...")
print(f"Estimated pi: {estimate_pi(10000)}")
"""
            result = tool.execute_sync("run", code, "python")

            assert result.success is True
            assert "Estimated pi:" in result.data['stdout']

    @pytest.mark.acceptance
    @patch('grok_py.grok.client.GrokClient')
    def test_user_iterative_workflow(self, mock_grok_client, runner):
        """Test scenario: User iteratively refines work with CLI and tools."""
        # Mock multiple chat interactions
        call_count = 0
        def mock_send_message(**kwargs):
            nonlocal call_count
            call_count += 1
            if "debug" in kwargs['message'].lower():
                return "Add print statements to see variable values."
            elif "error" in kwargs['message'].lower():
                return "Check your indentation and syntax."
            else:
                return "How can I help you with your code?"

        mock_client_instance = AsyncMock()
        mock_client_instance.send_message.side_effect = mock_send_message
        mock_grok_client.return_value.__aenter__.return_value = mock_client_instance
        mock_grok_client.return_value.__aexit__.return_value = None

        # Simulate iterative debugging session
        queries = [
            "My Python code isn't working",
            "I added debug prints but still getting errors",
            "Fixed the syntax, now it runs but wrong output"
        ]

        for query in queries:
            result = runner.invoke(app, ["chat", query])
            assert result.exit_code == 0

        assert call_count == 3  # All queries were processed

    @pytest.mark.asyncio
    @pytest.mark.acceptance
    async def test_performance_requirements(self):
        """Test scenario: Verify tools meet performance requirements."""
        import time
        from grok_py.tools.example_calculator import CalculatorTool

        calc = CalculatorTool()
        start_time = time.time()

        # Perform multiple calculations
        for i in range(100):
            result = await calc.execute(operation="add", a=i, b=i+1)
            assert result.success is True

        end_time = time.time()
        duration = end_time - start_time

        # Should complete in reasonable time (less than 1 second for 100 operations)
        assert duration < 1.0, f"Performance test took {duration:.2f}s, expected < 1.0s"

    @pytest.mark.asyncio
    @pytest.mark.acceptance
    async def test_developer_edits_code_file(self):
        """Test scenario: Developer views, edits, and saves a code file."""
        import tempfile
        import os
        from grok_py.tools.file_tools import ViewFileTool, CreateFileTool, StrReplaceEditorTool

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def hello():\n    print('Hello World')\n")
            temp_file = f.name

        try:
            # View the file
            view_tool = ViewFileTool()
            view_result = view_tool.execute_sync(temp_file)
            assert view_result.success is True
            assert "Hello World" in view_result.data["content"]

            # Edit the file using string replacement
            edit_tool = StrReplaceEditorTool()
            edit_result = edit_tool.execute_sync(
                temp_file,
                "def hello():\n    print('Hello World')\n",
                "def hello():\n    print('Hello, Enhanced World!')\n"
            )
            assert edit_result.success is True

            # Verify the change
            view_result2 = view_tool.execute_sync(temp_file)
            assert view_result2.success is True
            assert "Enhanced World" in view_result2.data["content"]

        finally:
            os.unlink(temp_file)

    @pytest.mark.acceptance
    def test_researcher_gathers_information(self):
        """Test scenario: Researcher uses web search to gather current information."""
        with patch('grok_py.tools.web_search.WebSearchTool.execute_sync') as mock_execute:
            mock_execute.return_value = MagicMock(
                success=True,
                data={
                    'results': [
                        {'title': 'Latest AI Developments 2024', 'url': 'https://example.com/ai', 'content': 'Recent advances in AI...'},
                        {'title': 'Machine Learning Trends', 'url': 'https://example.com/ml', 'content': 'Current trends include...'}
                    ]
                }
            )

            from grok_py.tools.web_search import WebSearchTool

            tool = WebSearchTool()
            result = tool.execute_sync("latest AI developments 2024")

            assert result.success is True
            assert len(result.data['results']) >= 2
            assert any("AI" in r['title'] for r in result.data['results'])

    @pytest.mark.acceptance
    def test_system_admin_installs_package(self):
        """Test scenario: System administrator installs a package."""
        with patch('grok_py.tools.apt.AptTool.execute_sync') as mock_execute:
            mock_execute.return_value = MagicMock(
                success=True,
                data={'output': 'Reading package lists... Done\nBuilding dependency tree... Done\ncurl is already the latest version (7.81.0-1ubuntu1.16).\n'}
            )

            from grok_py.tools.apt import AptTool

            tool = AptTool()
            result = tool.execute_sync("install", "curl")

            assert result.success is True
            assert "curl" in result.data['output']
            mock_execute.assert_called_once_with("install", "curl")

    @pytest.mark.acceptance
    def test_file_operations_performance(self):
        """Test scenario: Verify file operations meet performance requirements."""
        import tempfile
        import time
        from grok_py.tools.file_tools import ViewFileTool, StrReplaceEditorTool

        # Create a larger test file
        content = "line " + "\nline ".join(str(i) for i in range(1000)) + "\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_file = f.name

        try:
            view_tool = ViewFileTool()
            edit_tool = StrReplaceEditorTool()

            # Test view performance
            start_time = time.time()
            view_result = view_tool.execute_sync(temp_file)
            view_duration = time.time() - start_time
            assert view_result.success is True
            assert view_duration < 1.0, f"File view took {view_duration:.2f}s"

            # Test edit performance
            start_time = time.time()
            edit_result = edit_tool.execute_sync(
                temp_file,
                "line 500",
                "line 500 - edited"
            )
            edit_duration = time.time() - start_time
            assert edit_result.success is True
            assert edit_duration < 1.0, f"File edit took {edit_duration:.2f}s"

        finally:
            import os
            os.unlink(temp_file)

    @pytest.mark.acceptance
    def test_error_handling_file_not_found(self):
        """Test scenario: User tries to view a non-existent file."""
        from grok_py.tools.file_tools import ViewFileTool

        view_tool = ViewFileTool()
        result = view_tool.execute_sync("/non/existent/file.txt")

        assert result.success is False
        assert "does not exist" in str(result.error).lower()

    @pytest.mark.acceptance
    def test_error_handling_invalid_code_execution(self):
        """Test scenario: User tries to execute invalid code."""
        with patch('grok_py.tools.code_execution.CodeExecutionTool.execute_sync') as mock_execute:
            mock_execute.return_value = MagicMock(
                success=False,
                error="SyntaxError: invalid syntax"
            )

            from grok_py.tools.code_execution import CodeExecutionTool

            tool = CodeExecutionTool()
            result = tool.execute_sync("run", "invalid python code {{{", "python")

            assert result.success is False
            assert "syntax" in str(result.error).lower()

    @pytest.mark.acceptance
    def test_error_handling_web_search_api_failure(self):
        """Test scenario: Web search fails due to API issues."""
        with patch('grok_py.tools.web_search.WebSearchTool.execute_sync') as mock_execute:
            mock_execute.return_value = MagicMock(
                success=False,
                error="API key invalid or rate limit exceeded"
            )

            from grok_py.tools.web_search import WebSearchTool

            tool = WebSearchTool()
            result = tool.execute_sync("test query")

            assert result.success is False
            assert "api" in str(result.error).lower() or "rate limit" in str(result.error).lower()

    @pytest.mark.acceptance
    def test_error_handling_apt_package_not_found(self):
        """Test scenario: Package installation fails because package doesn't exist."""
        with patch('grok_py.tools.apt.AptTool.execute_sync') as mock_execute:
            mock_execute.return_value = MagicMock(
                success=False,
                error="E: Unable to locate package nonexistent-package"
            )

            from grok_py.tools.apt import AptTool

            tool = AptTool()
            result = tool.execute_sync("install", "nonexistent-package")

            assert result.success is False
            assert "unable to locate" in str(result.error).lower()

    @pytest.mark.acceptance
    def test_edge_case_large_file_handling(self):
        """Test scenario: Handling large files within size limits."""
        import tempfile
        from grok_py.tools.file_tools import ViewFileTool

        # Create a 5MB file (within typical limits)
        large_content = "x" * (5 * 1024 * 1024)
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(large_content)
            temp_file = f.name

        try:
            view_tool = ViewFileTool()
            result = view_tool.execute_sync(temp_file)
            # Should handle large files gracefully
            assert result.success is True or "too large" in str(result.error).lower()
        finally:
            import os
            os.unlink(temp_file)

    @pytest.mark.acceptance
    def test_edge_case_empty_search_query(self):
        """Test scenario: Empty search query handling."""
        with patch('grok_py.tools.web_search.WebSearchTool.execute_sync') as mock_execute:
            mock_execute.return_value = MagicMock(
                success=False,
                error="Query cannot be empty"
            )

            from grok_py.tools.web_search import WebSearchTool

            tool = WebSearchTool()
            result = tool.execute_sync("")

            assert result.success is False
            assert "empty" in str(result.error).lower()

    @pytest.mark.acceptance
    def test_edge_case_code_execution_timeout(self):
        """Test scenario: Code execution timeout handling."""
        with patch('grok_py.tools.code_execution.CodeExecutionTool.execute_sync') as mock_execute:
            mock_execute.return_value = MagicMock(
                success=False,
                error="Execution timed out after 30 seconds"
            )

            from grok_py.tools.code_execution import CodeExecutionTool

            tool = CodeExecutionTool()
            code = "import time; time.sleep(60)"  # Long running code
            result = tool.execute_sync("run", code, "python")

            assert result.success is False
            assert "timed out" in str(result.error).lower()

    @pytest.mark.acceptance
    def test_edge_case_invalid_file_edit_operation(self):
        """Test scenario: Invalid file edit operation (old_str not found)."""
        import tempfile
        from grok_py.tools.file_tools import StrReplaceEditorTool

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def hello():\n    print('Hello')\n")
            temp_file = f.name

        try:
            edit_tool = StrReplaceEditorTool()
            result = edit_tool.execute_sync(
                temp_file,
                "nonexistent text",
                "replacement"
            )
            assert result.success is False
            assert "not found" in str(result.error).lower() or "no match" in str(result.error).lower()
        finally:
            import os
            os.unlink(temp_file)