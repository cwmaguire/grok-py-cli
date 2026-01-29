"""Enhanced safe code execution tool using Docker containers with advanced security."""

import subprocess
import shlex
import tempfile
import os
import uuid
import time
import logging
from typing import Optional

from .base import SyncTool, ToolCategory, ToolResult
from ..utils.sandbox import (
    DockerManager, SecurityUtils, LanguageDetector, PackageManager, Language
)

logger = logging.getLogger(__name__)


class CodeExecutionTool(SyncTool):
    """Enhanced tool for safe code execution in isolated Docker containers with advanced security."""

    def __init__(self):
        super().__init__(
            name="code_execution",
            description="Safely execute code snippets in Docker containers with advanced security, multi-language support, and dependency management",
            category=ToolCategory.DEVELOPMENT
        )

        # Initialize sandbox components
        self.docker_manager = DockerManager()
        self.security_utils = SecurityUtils()
        self.language_detector = LanguageDetector()
        self.package_manager = PackageManager(self.docker_manager)

    def execute_sync(
        self,
        operation: str,
        code: str,
        language: Optional[str] = None,
        input: Optional[str] = None
    ) -> ToolResult:
        """Execute code in a safe Docker container with enhanced security.

        Args:
            operation: Operation to perform ('run' or 'test')
            code: Code to execute
            language: Programming language (auto-detected if not provided)
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

            # Detect or validate language
            if language:
                try:
                    detected_lang = Language(language.lower())
                except ValueError:
                    return ToolResult(
                        success=False,
                        error=f"Unsupported language: {language}"
                    )
            else:
                # Auto-detect language
                detected_lang = self.language_detector.detect(code)
                logger.info(f"Auto-detected language: {detected_lang.value}")

            logger.info(f"About to call _execute_code_secure with language {detected_lang.value}")
            # Execute the code with enhanced security
            return self._execute_code_secure(code, detected_lang, input, operation == 'test')

        except Exception as e:
            logger.error(f"Code execution failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Code execution failed: {str(e)}"
            )

    def _execute_code_secure(
        self,
        code: str,
        language: Language,
        input_data: Optional[str],
        is_test: bool
    ) -> ToolResult:
        """Execute code in Docker container with enhanced security and monitoring."""
        # Generate unique container name
        container_name = f"grok-code-exec-{uuid.uuid4().hex[:8]}"

        try:
            # Analyze code for security
            code_analysis = self.security_utils.analyze_and_log_execution(
                code, language.value, container_name, 'test' if is_test else 'run'
            )

            # Prepare execution environment with dependencies
            config, dep_info = self.package_manager.prepare_execution_environment(
                code, language, container_name
            )

            # Ensure Docker image is available
            if not self.docker_manager.pull_image(config.image):
                return ToolResult(
                    success=False,
                    error=f"Failed to pull Docker image: {config.image}"
                )

            # Create container configuration with enhanced security
            container_config = self._create_secure_container_config(config, dep_info)

            # Write code to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix=config.extensions[0], delete=False) as code_file:
                code_file.write(code)
                code_file_path = code_file.name

            # Add code file to volumes
            code_filename = f"code{config.extensions[0]}"
            container_config.volumes[code_file_path] = f"/tmp/{code_filename}:ro"

            # Update command to use the correct filename
            container_config.command = [cmd.replace(f"/tmp/code{config.extensions[0]}", f"/tmp/{code_filename}")
                                       for cmd in config.command]

            # Execute with timeout
            timeout_seconds = 30 if not is_test else 60

            start_time = time.time()
            result = self.docker_manager.run_container(
                container_config,
                container_name,
                input_data=input_data,
                timeout=timeout_seconds
            )
            execution_time = time.time() - start_time

            # Log execution result
            anomalies = []  # Could be enhanced with process monitoring
            code_hash = self.security_utils.hash_code(code)
            self.security_utils.log_execution_result(
                container_name, language.value, code_hash,
                result.success, execution_time, result.exit_code, anomalies
            )

            # Determine success with enhanced error checking
            success = result.success
            if success and result.stderr.strip():
                # Enhanced error detection
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
                'exit_code': result.exit_code,
                'container_name': container_name,
                'execution_time': execution_time,
                'security_analysis': {
                    'risk_score': code_analysis.risk_score,
                    'has_dependencies': dep_info.has_dependencies,
                    'suspicious_patterns': len(code_analysis.suspicious_patterns),
                }
            }

            return ToolResult(
                success=success,
                data=result_data,
                error=result.stderr.strip() if not success and result.stderr.strip() else None,
                metadata={
                    'exit_code': result.exit_code,
                    'has_output': bool(result.stdout.strip()),
                    'has_error': bool(result.stderr.strip()),
                    'language': language.value,
                    'timed_out': False,
                    'container_name': container_name,
                    'execution_time': execution_time,
                    'risk_score': code_analysis.risk_score,
                }
            )

        except Exception as e:
            logger.error(f"Error in secure code execution: {e}")

            # Log the error
            code_hash = self.security_utils.hash_code(code)
            self.security_utils.log_execution_result(
                container_name, language.value, code_hash,
                False, 0, -1, [str(e)]
            )

            # Cleanup
            self.docker_manager._cleanup_container(container_name)
            if 'code_file_path' in locals():
                os.unlink(code_file_path)

            return ToolResult(
                success=False,
                error=f"Code execution failed: {str(e)}"
            )

    def _create_secure_container_config(self, config, dep_info):
        """Create a secure container configuration."""
        from ..utils.sandbox.docker_manager import ContainerConfig

        # Base security settings
        container_config = ContainerConfig(
            image=config.image,
            command=config.command,
            memory_limit="512m",  # Increased for dependencies
            cpu_limit="1.0",      # Increased for better performance
            network_mode="none",  # Strict network isolation
            read_only=True,
            tmpfs_size="200m",    # Larger tmpfs for dependencies
        )

        # Enhanced security options
        container_config.security_opts.extend([
            "--security-opt=no-new-privileges:true",
            "--security-opt=seccomp=unconfined",  # Could be more restrictive
        ])

        # Add environment variables for security
        container_config.env_vars.update({
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "HOME": "/tmp",
            "USER": "sandbox",
        })

        return container_config

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
            config = self.package_manager.get_config(lang)
            return {
                'name': config.name,
                'extensions': config.extensions,
                'image': config.image,
                'package_manager': config.package_manager,
            }
        except ValueError:
            return {}</content>
