"""Safe code execution tool using direct subprocess execution."""

import subprocess
import shlex
import tempfile
import os
import uuid
import time
import logging
from typing import Optional
from enum import Enum

from .base import SyncTool, ToolCategory, ToolResult

logger = logging.getLogger(__name__)


class Language(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    BASH = "bash"


class CodeExecutionTool(SyncTool):
    """Tool for safe code execution directly via subprocess."""

    def __init__(self):
        super().__init__(
            name="code_execution",
            description="Safely execute code snippets directly via subprocess with multi-language support",
            category=ToolCategory.DEVELOPMENT
        )

    def execute_sync(
        self,
        operation: str,
        code: str,
        language: Optional[str] = None,
        input: Optional[str] = None
    ) -> ToolResult:
        """Execute code directly via subprocess.

        Args:
            operation: Operation to perform ('run' or 'test')
            code: Code to execute
            language: Programming language (required)
            input: Optional input to provide to the code execution (passed via stdin)

        Returns:
            ToolResult with execution result
        """
        logger.info(f"CodeExecutionTool.execute_sync called with language={language}, operation={operation}")
        try:
            # Validate operation
            if operation not in ['run', 'test']:
                return ToolResult(
                    success=False,
                    error=f"Invalid operation: {operation}. Valid operations: run, test"
                )

            # Validate code
            if not code or not code.strip():
                return ToolResult(
                    success=False,
                    error="Code cannot be empty"
                )

            # Validate language
            if not language:
                return ToolResult(
                    success=False,
                    error="Language must be specified"
                )

            try:
                detected_lang = Language(language.lower())
            except ValueError:
                return ToolResult(
                    success=False,
                    error=f"Unsupported language: {language}. Supported: {[l.value for l in Language]}"
                )

            logger.info(f"About to execute code with language {detected_lang.value}")
            # Execute the code directly
            return self._execute_code_direct(code, detected_lang, input, operation == 'test')

        except Exception as e:
            logger.error(f"Code execution failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Code execution failed: {str(e)}"
            )

    def _execute_code_direct(
        self,
        code: str,
        language: Language,
        input_data: Optional[str],
        is_test: bool
    ) -> ToolResult:
        """Execute code directly via subprocess."""
        # Generate unique execution id
        exec_id = f"grok-code-exec-{uuid.uuid4().hex[:8]}"

        try:
            # Write code to temporary file
            suffix = {
                Language.PYTHON: '.py',
                Language.JAVASCRIPT: '.js',
                Language.BASH: '.sh'
            }.get(language, '.txt')

            with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as code_file:
                code_file.write(code)
                code_file_path = code_file.name

            # Ensure the file is readable
            os.chmod(code_file_path, 0o644)

            # Determine command
            commands = {
                Language.PYTHON: ['python3', code_file_path],
                Language.JAVASCRIPT: ['node', code_file_path],
                Language.BASH: ['bash', code_file_path]
            }

            cmd = commands.get(language)
            if not cmd:
                os.unlink(code_file_path)
                return ToolResult(
                    success=False,
                    error=f"No command defined for language: {language.value}"
                )

            # Execute with timeout
            timeout_seconds = 30 if not is_test else 60

            start_time = time.time()
            try:
                result = subprocess.run(
                    cmd,
                    input=input_data,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds
                )
                execution_time = time.time() - start_time

                # Determine success
                success = result.returncode == 0
                if success and result.stderr.strip():
                    # Basic error detection
                    error_indicators = [
                        'error', 'exception', 'traceback', 'compilation failed',
                        'segmentation fault', 'runtime error', 'panic'
                    ]
                    if any(indicator in result.stderr.lower() for indicator in error_indicators):
                        success = False

                # Prepare result data
                result_data = {
                    'operation': 'test' if is_test else 'run',
                    'language': language.value,
                    'code': code,
                    'input': input_data,
                    'stdout': result.stdout.strip(),
                    'stderr': result.stderr.strip(),
                    'exit_code': result.returncode,
                    'exec_id': exec_id,
                    'execution_time': execution_time,
                }

                return ToolResult(
                    success=success,
                    data=result_data,
                    error=result.stderr.strip() if not success and result.stderr.strip() else None,
                    metadata={
                        'exit_code': result.returncode,
                        'has_output': bool(result.stdout.strip()),
                        'has_error': bool(result.stderr.strip()),
                        'language': language.value,
                        'timed_out': False,
                        'exec_id': exec_id,
                        'execution_time': execution_time,
                    }
                )

            except subprocess.TimeoutExpired:
                execution_time = time.time() - start_time
                os.unlink(code_file_path)
                return ToolResult(
                    success=False,
                    error="Code execution timed out",
                    metadata={
                        'timed_out': True,
                        'execution_time': execution_time,
                        'language': language.value,
                    }
                )

        except Exception as e:
            logger.error(f"Error in direct code execution: {e}")
            if 'code_file_path' in locals():
                os.unlink(code_file_path)
            return ToolResult(
                success=False,
                error=f"Code execution failed: {str(e)}"
            )
        finally:
            if 'code_file_path' in locals():
                try:
                    os.unlink(code_file_path)
                except:
                    pass

    def get_supported_languages(self) -> list:
        """Get list of supported programming languages."""
        return [lang.value for lang in Language]

    def validate_language_support(self, language: str) -> bool:
        """Check if a language is supported."""
        try:
            Language(language.lower())
            return True
        except ValueError:
            return False

    def get_language_config(self, language: str) -> dict:
        """Get configuration for a specific language."""
        try:
            lang = Language(language.lower())
            configs = {
                Language.PYTHON: {'name': 'Python', 'extensions': ['.py'], 'interpreter': 'python3'},
                Language.JAVASCRIPT: {'name': 'JavaScript', 'extensions': ['.js'], 'interpreter': 'node'},
                Language.BASH: {'name': 'Bash', 'extensions': ['.sh'], 'interpreter': 'bash'}
            }
            return configs.get(lang, {})
        except ValueError:
            return {}
