"""Safe code execution tool using Docker containers."""

import subprocess
import shlex
import tempfile
import os
import uuid
from typing import Optional

from .base import SyncTool, ToolCategory, ToolResult


class CodeExecutionTool(SyncTool):
    """Tool for safe code execution in isolated Docker containers."""

    # Supported languages and their Docker images
    LANGUAGE_CONFIGS = {
        'javascript': {
            'image': 'node:18-alpine',
            'extension': '.js',
            'command': ['node', '/tmp/code.js']
        },
        'typescript': {
            'image': 'node:18-alpine',
            'extension': '.ts',
            'command': ['npx', 'ts-node', '/tmp/code.ts']
        },
        'python': {
            'image': 'python:3.11-alpine',
            'extension': '.py',
            'command': ['python', '/tmp/code.py']
        },
        'python3': {
            'image': 'python:3.11-alpine',
            'extension': '.py',
            'command': ['python3', '/tmp/code.py']
        },
        'java': {
            'image': 'openjdk:17-alpine',
            'extension': '.java',
            'command': ['sh', '-c', 'javac /tmp/code.java && java -cp /tmp Main']
        },
        'cpp': {
            'image': 'gcc:11-alpine',
            'extension': '.cpp',
            'command': ['sh', '-c', 'g++ /tmp/code.cpp -o /tmp/code && /tmp/code']
        },
        'c': {
            'image': 'gcc:11-alpine',
            'extension': '.c',
            'command': ['sh', '-c', 'gcc /tmp/code.c -o /tmp/code && /tmp/code']
        },
        'go': {
            'image': 'golang:1.21-alpine',
            'extension': '.go',
            'command': ['go', 'run', '/tmp/code.go']
        },
        'rust': {
            'image': 'rust:1.70-alpine',
            'extension': '.rs',
            'command': ['sh', '-c', 'rustc /tmp/code.rs -o /tmp/code && /tmp/code']
        },
        'bash': {
            'image': 'alpine:latest',
            'extension': '.sh',
            'command': ['bash', '/tmp/code.sh']
        },
        'shell': {
            'image': 'alpine:latest',
            'extension': '.sh',
            'command': ['sh', '/tmp/code.sh']
        },
        'sh': {
            'image': 'alpine:latest',
            'extension': '.sh',
            'command': ['sh', '/tmp/code.sh']
        }
    }

    def __init__(self):
        super().__init__(
            name="code_execution",
            description="Safely execute code snippets in Docker containers (JavaScript, Python, Java, C++, Go, Rust, Bash)",
            category=ToolCategory.DEVELOPMENT
        )

    def execute_sync(
        self,
        operation: str,
        code: str,
        language: str,
        input: Optional[str] = None
    ) -> ToolResult:
        """Execute code in a safe Docker container.

        Args:
            operation: Operation to perform ('run' or 'test')
            code: Code to execute
            language: Programming language (javascript, python, java, cpp, go, rust, bash, etc.)
            input: Optional input to provide to the code execution (passed via stdin)

        Returns:
            ToolResult with execution result
        """
        try:
            # Validate operation
            if operation not in ['run', 'test']:
                return ToolResult(
                    success=False,
                    error=f"Invalid operation: {operation}. Valid operations: run, test"
                )

            # Validate language
            if language not in self.LANGUAGE_CONFIGS:
                return ToolResult(
                    success=False,
                    error=f"Unsupported language: {language}. Supported: {', '.join(self.LANGUAGE_CONFIGS.keys())}"
                )

            # Validate code
            if not code or not code.strip():
                return ToolResult(
                    success=False,
                    error="Code cannot be empty"
                )

            # Execute the code
            return self._execute_code(code, language, input, operation == 'test')

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Code execution failed: {str(e)}"
            )

    def _execute_code(self, code: str, language: str, input_data: Optional[str], is_test: bool) -> ToolResult:
        """Execute code in Docker container."""
        config = self.LANGUAGE_CONFIGS[language]

        # Generate unique container name
        container_name = f"grok-code-exec-{uuid.uuid4().hex[:8]}"

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write code to temporary file
                code_file = os.path.join(temp_dir, f'code{config["extension"]}')
                with open(code_file, 'w', encoding='utf-8') as f:
                    f.write(code)

                # Prepare Docker command
                docker_cmd = [
                    'docker', 'run',
                    '--rm',
                    '--name', container_name,
                    '--network', 'none',  # Isolate network
                    '--memory', '256m',    # Memory limit
                    '--cpus', '0.5',       # CPU limit
                    '--read-only',         # Read-only filesystem
                    '--tmpfs', '/tmp:rw,noexec,nosuid,size=100m',  # Temporary writable directory
                    '--cap-drop=all',      # Drop all capabilities
                    '--security-opt=no-new-privileges:true',
                ]

                # Mount code file
                docker_cmd.extend(['-v', f'{code_file}:/tmp/code{config["extension"]}:ro'])

                # Add image and command
                docker_cmd.append(config['image'])
                docker_cmd.extend(config['command'])

                command_str = shlex.join(docker_cmd)

                # Execute with timeout
                timeout_seconds = 30 if not is_test else 60  # Longer timeout for tests

                if input_data:
                    # Provide input via stdin
                    result = subprocess.run(
                        docker_cmd,
                        input=input_data,
                        capture_output=True,
                        text=True,
                        timeout=timeout_seconds
                    )
                else:
                    result = subprocess.run(
                        docker_cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout_seconds
                    )

                # Prepare result data
                result_data = {
                    'operation': 'run' if not is_test else 'test',
                    'language': language,
                    'code': code,
                    'input': input_data,
                    'command': command_str,
                    'stdout': result.stdout.strip(),
                    'stderr': result.stderr.strip(),
                    'exit_code': result.returncode,
                    'container_name': container_name
                }

                # Determine success (exit code 0 is typically success)
                success = result.returncode == 0

                # For some languages/compilation errors, check stderr
                if success and result.stderr.strip():
                    # Some warnings are ok, but compilation errors should fail
                    if any(error_indicator in result.stderr.lower() for error_indicator in
                           ['error', 'exception', 'traceback', 'compilation failed']):
                        success = False

                return ToolResult(
                    success=success,
                    data=result_data,
                    error=result.stderr.strip() if not success and result.stderr.strip() else None,
                    metadata={
                        'exit_code': result.returncode,
                        'has_output': bool(result.stdout.strip()),
                        'has_error': bool(result.stderr.strip()),
                        'language': language,
                        'timed_out': False,
                        'container_name': container_name
                    }
                )

        except subprocess.TimeoutExpired:
            # Try to clean up container if it still exists
            try:
                subprocess.run(['docker', 'rm', '-f', container_name],
                             capture_output=True, timeout=5)
            except:
                pass

            return ToolResult(
                success=False,
                error=f"Code execution timed out after {timeout_seconds} seconds",
                metadata={'timed_out': True, 'container_name': container_name}
            )
        except FileNotFoundError:
            return ToolResult(
                success=False,
                error="Docker not found. Please ensure Docker is installed and running."
            )
        except subprocess.CalledProcessError as e:
            return ToolResult(
                success=False,
                error=f"Docker execution failed: {e.stderr}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Unexpected error during code execution: {str(e)}"
            )

    def get_supported_languages(self) -> list:
        """Get list of supported programming languages."""
        return list(self.LANGUAGE_CONFIGS.keys())

    def validate_language_support(self, language: str) -> bool:
        """Check if a language is supported."""
        return language in self.LANGUAGE_CONFIGS

    def get_language_config(self, language: str) -> dict:
        """Get configuration for a specific language."""
        return self.LANGUAGE_CONFIGS.get(language, {})</content>
</xai:function_call">The Code Execution Tool implementation provides safe code execution in Docker containers with comprehensive security measures. It supports multiple programming languages (JavaScript, TypeScript, Python, Java, C++, Go, Rust, Bash) with appropriate Docker images and execution commands.

Key security features include:
- Network isolation (--network none)
- Memory and CPU limits
- Read-only filesystem with limited tmpfs
- Dropped capabilities
- No new privileges

The tool handles input/output via stdin/stdout, includes timeout management, and provides detailed error reporting. For each language, it uses the most appropriate Docker base image and compilation/execution commands.

Moving on to the Web Search Tool next, which will integrate with the Tavily API for web search functionality. Let me mark the code execution tool as complete and start on the web search tool. 

<xai:function_call name="update_todo_list">
<parameter name="updates">[{"id":"implement_code_execution_tool","status":"completed"},{"id":"implement_web_search_tool","status":"in_progress"}] 

Now I need to implement the Web Search Tool using Tavily API. I need to check if TAVILY_API_KEY environment variable is available, and implement the search functionality with different search depths and topics.

Let me implement this tool. It should support query, max_results, search_depth, and topic parameters. 

<xai:function_call name="create_file">
<parameter name="path">grok_py/tools/web_search.py