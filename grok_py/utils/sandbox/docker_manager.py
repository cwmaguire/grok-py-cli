"""Docker container management for code execution sandbox."""

import subprocess
import shlex
import logging
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ContainerConfig:
    """Configuration for container execution."""
    image: str
    command: List[str]
    memory_limit: str = "256m"
    cpu_limit: str = "0.5"
    network_mode: str = "none"
    read_only: bool = True
    tmpfs_size: str = "100m"
    capabilities: List[str] = None
    env_vars: Dict[str, str] = None
    volumes: Dict[str, str] = None
    security_opts: List[str] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = ["--cap-drop=all"]
        if self.env_vars is None:
            self.env_vars = {}
        if self.volumes is None:
            self.volumes = {}
        if self.security_opts is None:
            self.security_opts = ["--security-opt=no-new-privileges:true"]


@dataclass
class ExecutionResult:
    """Result of container execution."""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    container_id: Optional[str] = None
    logs: Optional[str] = None


class DockerManager:
    """Manages Docker containers for secure code execution."""

    def __init__(self, base_images_dir: Optional[str] = None):
        self.base_images_dir = Path(base_images_dir) if base_images_dir else Path.home() / ".grok" / "docker_images"
        self.base_images_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_docker_available()

    def _ensure_docker_available(self) -> None:
        """Ensure Docker is available and running."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError(f"Docker not available: {result.stderr}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(f"Docker not found or not running: {e}")

    def pull_image(self, image: str, timeout: int = 300) -> bool:
        """Pull a Docker image if not already available."""
        try:
            # Check if image exists locally
            result = subprocess.run(
                ["docker", "images", "-q", image],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and result.stdout.strip():
                logger.info(f"Image {image} already available locally")
                return True

            # Pull the image
            logger.info(f"Pulling image {image}")
            result = subprocess.run(
                ["docker", "pull", image],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                logger.error(f"Failed to pull image {image}: {result.stderr}")
                return False

            logger.info(f"Successfully pulled image {image}")
            return True

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout pulling image {image}")
            return False
        except Exception as e:
            logger.error(f"Error pulling image {image}: {e}")
            return False

    def build_custom_image(self, image_name: str, dockerfile_content: str, context_dir: Path) -> bool:
        """Build a custom Docker image."""
        try:
            # Write Dockerfile to context directory
            dockerfile_path = context_dir / "Dockerfile"
            dockerfile_path.write_text(dockerfile_content)

            cmd = ["docker", "build", "-t", image_name, str(context_dir)]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes
            )

            if result.returncode != 0:
                logger.error(f"Failed to build image {image_name}: {result.stderr}")
                return False

            logger.info(f"Successfully built custom image {image_name}")
            return True

        except Exception as e:
            logger.error(f"Error building custom image {image_name}: {e}")
            return False

    def run_container(
        self,
        config: ContainerConfig,
        container_name: str,
        input_data: Optional[str] = None,
        timeout: int = 30
    ) -> ExecutionResult:
        """Run a container with the given configuration."""
        import time
        start_time = time.time()

        try:
            # Build docker run command
            cmd = self._build_run_command(config, container_name)

            logger.debug(f"Running container command: {shlex.join(cmd)}")

            # Execute the container
            if input_data:
                result = subprocess.run(
                    cmd,
                    input=input_data,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
            else:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

            execution_time = time.time() - start_time

            # Get container logs if execution failed
            logs = None
            if result.returncode != 0:
                logs = self._get_container_logs(container_name)

            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                execution_time=execution_time,
                container_id=container_name,
                logs=logs
            )

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            # Force remove the container
            self._cleanup_container(container_name)

            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Execution timed out after {timeout} seconds",
                exit_code=-1,
                execution_time=execution_time,
                container_id=container_name
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error running container {container_name}: {e}")
            self._cleanup_container(container_name)

            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time=execution_time,
                container_id=container_name
            )

    def _build_run_command(self, config: ContainerConfig, container_name: str) -> List[str]:
        """Build the docker run command from configuration."""
        cmd = [
            "docker", "run",
            "--rm",
            "--name", container_name,
            "--network", config.network_mode,
            "--memory", config.memory_limit,
            "--cpus", config.cpu_limit,
        ]

        if config.read_only:
            cmd.append("--read-only")

        cmd.extend([
            "--tmpfs", f"/tmp:rw,noexec,nosuid,size={config.tmpfs_size}",
        ])

        # Add capabilities
        for cap in config.capabilities:
            cmd.append(cap)

        # Add security options
        for opt in config.security_opts:
            cmd.append(opt)

        # Add environment variables
        for key, value in config.env_vars.items():
            cmd.extend(["--env", f"{key}={value}"])

        # Add volumes
        for host_path, container_path in config.volumes.items():
            cmd.extend(["-v", f"{host_path}:{container_path}"])

        # Add image
        cmd.append(config.image)

        # Add command
        cmd.extend(config.command)

        return cmd

    def _get_container_logs(self, container_name: str) -> Optional[str]:
        """Get logs from a container."""
        try:
            result = subprocess.run(
                ["docker", "logs", container_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout if result.returncode == 0 else None
        except Exception:
            return None

    def _cleanup_container(self, container_name: str) -> None:
        """Force remove a container if it exists."""
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True,
                timeout=10
            )
        except Exception as e:
            logger.warning(f"Failed to cleanup container {container_name}: {e}")

    def list_containers(self, filter_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List running containers, optionally filtered by name."""
        try:
            cmd = ["docker", "ps", "--format", "json"]
            if filter_name:
                cmd.extend(["--filter", f"name={filter_name}"])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                containers = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            containers.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
                return containers
            return []
        except Exception as e:
            logger.error(f"Error listing containers: {e}")
            return []

    def prune_images(self) -> bool:
        """Remove unused Docker images to free up space."""
        try:
            result = subprocess.run(
                ["docker", "image", "prune", "-f"],
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error pruning images: {e}")
            return False