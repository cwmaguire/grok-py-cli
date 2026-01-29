"""Language detection and package management utilities."""

import re
import os
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .docker_manager import DockerManager, ContainerConfig, ExecutionResult


class Language(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    PYTHON3 = "python3"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    C = "c"
    GO = "go"
    RUST = "rust"
    BASH = "bash"
    SHELL = "shell"
    SH = "sh"


@dataclass
class LanguageConfig:
    """Configuration for a programming language."""
    name: str
    extensions: List[str]
    image: str
    command: List[str]
    package_manager: Optional[str] = None
    install_command: Optional[List[str]] = None
    dependency_file: Optional[str] = None


@dataclass
class DependencyInfo:
    """Information about code dependencies."""
    has_dependencies: bool = False
    dependency_file: Optional[str] = None
    packages: List[str] = None
    cache_key: Optional[str] = None

    def __post_init__(self):
        if self.packages is None:
            self.packages = []


class LanguageDetector:
    """Detects programming language from code snippets or file extensions."""

    # Language patterns for detection
    LANGUAGE_PATTERNS = {
        Language.PYTHON: [
            r'^\s*(import|from)\s+\w+',
            r'^\s*def\s+\w+\s*\(',
            r'^\s*class\s+\w+',
            r'^\s*if\s+__name__\s*==\s*[\'"]__main__[\'"]',
            r'\bprint\s*\(',
        ],
        Language.JAVASCRIPT: [
            r'\bfunction\s+\w+\s*\(',
            r'\bconst\s+\w+\s*=',
            r'\blet\s+\w+\s*=',
            r'\bvar\s+\w+\s*=',
            r'\bconsole\.log\s*\(',
            r'\brequire\s*\(',
        ],
        Language.TYPESCRIPT: [
            r'\binterface\s+\w+',
            r'\btype\s+\w+\s*=',
            r':\s*(string|number|boolean|any)',
            r'\bimport\s+.*from\s+',
        ],
        Language.JAVA: [
            r'\bpublic\s+class\s+\w+',
            r'\bpublic\s+static\s+void\s+main',
            r'\bSystem\.out\.println',
            r'\bimport\s+java\.',
        ],
        Language.CPP: [
            r'#include\s*<iostream>',
            r'\bstd::cout\s*<<',
            r'\bint\s+main\s*\(',
            r'\busing\s+namespace\s+std',
        ],
        Language.C: [
            r'#include\s*<stdio\.h>',
            r'\bprintf\s*\(',
            r'\bint\s+main\s*\(',
        ],
        Language.GO: [
            r'\bpackage\s+main',
            r'\bfunc\s+main\s*\(',
            r'\bimport\s+\(',
            r'\bfmt\.Println',
        ],
        Language.RUST: [
            r'\bfn\s+main\s*\(',
            r'\blet\s+mut\s+\w+',
            r'\bprintln!\s*\(',
            r'\buse\s+std::',
        ],
        Language.BASH: [
            r'^#!/bin/bash',
            r'^#!/bin/sh',
            r'\$\{\w+\}',
            r'\$\(\s*\w+',
        ],
    }

    EXTENSION_MAP = {
        '.py': Language.PYTHON,
        '.js': Language.JAVASCRIPT,
        '.ts': Language.TYPESCRIPT,
        '.java': Language.JAVA,
        '.cpp': Language.CPP,
        '.cc': Language.CPP,
        '.cxx': Language.CPP,
        '.c': Language.C,
        '.go': Language.GO,
        '.rs': Language.RUST,
        '.sh': Language.BASH,
        '.bash': Language.BASH,
    }

    def detect_from_extension(self, filename: str) -> Optional[Language]:
        """Detect language from file extension."""
        if not filename:
            return None

        _, ext = os.path.splitext(filename.lower())
        return self.EXTENSION_MAP.get(ext)

    def detect_from_code(self, code: str) -> Optional[Language]:
        """Detect language from code content."""
        if not code or not code.strip():
            return None

        scores = {}

        for language, patterns in self.LANGUAGE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, code, re.MULTILINE):
                    score += 1
            if score > 0:
                scores[language] = score

        if not scores:
            return None

        # Return language with highest score
        return max(scores, key=scores.get)

    def detect(self, code: str, filename: Optional[str] = None) -> Language:
        """Detect language from code and/or filename."""
        # First try extension detection
        if filename:
            ext_lang = self.detect_from_extension(filename)
            if ext_lang:
                return ext_lang

        # Fall back to code analysis
        code_lang = self.detect_from_code(code)
        if code_lang:
            return code_lang

        # Default to python if nothing detected
        return Language.PYTHON


class PackageManager:
    """Handles package management for different languages."""

    LANGUAGE_CONFIGS = {
        Language.PYTHON: LanguageConfig(
            name="python",
            extensions=[".py"],
            image="python:3.11-alpine",
            command=["python", "/tmp/code.py"],
            package_manager="pip",
            install_command=["pip", "install", "--user"],
            dependency_file="requirements.txt"
        ),
        Language.PYTHON3: LanguageConfig(
            name="python3",
            extensions=[".py"],
            image="python:3.11-alpine",
            command=["python3", "/tmp/code.py"],
            package_manager="pip",
            install_command=["pip", "install", "--user"],
            dependency_file="requirements.txt"
        ),
        Language.JAVASCRIPT: LanguageConfig(
            name="javascript",
            extensions=[".js"],
            image="node:18-alpine",
            command=["node", "/tmp/code.js"],
            package_manager="npm",
            install_command=["npm", "install"],
            dependency_file="package.json"
        ),
        Language.TYPESCRIPT: LanguageConfig(
            name="typescript",
            extensions=[".ts"],
            image="node:18-alpine",
            command=["npx", "ts-node", "/tmp/code.ts"],
            package_manager="npm",
            install_command=["npm", "install"],
            dependency_file="package.json"
        ),
        Language.JAVA: LanguageConfig(
            name="java",
            extensions=[".java"],
            image="openjdk:17-alpine",
            command=["sh", "-c", "javac /tmp/code.java && java -cp /tmp Main"],
            package_manager="maven",
            install_command=["mvn", "dependency:resolve"],
            dependency_file="pom.xml"
        ),
        Language.GO: LanguageConfig(
            name="go",
            extensions=[".go"],
            image="golang:1.21-alpine",
            command=["go", "run", "/tmp/code.go"],
            package_manager="go",
            install_command=["go", "mod", "download"],
            dependency_file="go.mod"
        ),
        Language.RUST: LanguageConfig(
            name="rust",
            extensions=[".rs"],
            image="rust:1.70-alpine",
            command=["sh", "-c", "rustc /tmp/code.rs -o /tmp/code && /tmp/code"],
            package_manager="cargo",
            install_command=["cargo", "build", "--release"],
            dependency_file="Cargo.toml"
        ),
        Language.BASH: LanguageConfig(
            name="bash",
            extensions=[".sh", ".bash"],
            image="alpine:latest",
            command=["bash", "/tmp/code.sh"]
        ),
        Language.SHELL: LanguageConfig(
            name="shell",
            extensions=[".sh"],
            image="alpine:latest",
            command=["sh", "/tmp/code.sh"]
        ),
        Language.SH: LanguageConfig(
            name="sh",
            extensions=[".sh"],
            image="alpine:latest",
            command=["sh", "/tmp/code.sh"]
        ),
        Language.CPP: LanguageConfig(
            name="cpp",
            extensions=[".cpp", ".cc", ".cxx"],
            image="gcc:11-alpine",
            command=["sh", "-c", "g++ /tmp/code.cpp -o /tmp/code && /tmp/code"]
        ),
        Language.C: LanguageConfig(
            name="c",
            extensions=[".c"],
            image="gcc:11-alpine",
            command=["sh", "-c", "gcc /tmp/code.c -o /tmp/code && /tmp/code"]
        ),
    }

    def __init__(self, docker_manager: DockerManager):
        self.docker_manager = docker_manager
        self.cache_dir = Path.home() / ".grok" / "package_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_config(self, language: Language) -> LanguageConfig:
        """Get configuration for a language."""
        return self.LANGUAGE_CONFIGS[language]

    def analyze_dependencies(self, code: str, language: Language) -> DependencyInfo:
        """Analyze code for dependencies."""
        config = self.get_config(language)
        info = DependencyInfo()

        if not config.package_manager:
            return info

        # Check for dependency indicators in code
        if language in [Language.PYTHON, Language.PYTHON3]:
            # Look for pip install patterns or requirements
            if re.search(r'\b(import|from)\s+(requests|numpy|pandas|flask|django)', code):
                info.has_dependencies = True
                info.packages = ['requests']  # Example, could be more sophisticated

        elif language in [Language.JAVASCRIPT, Language.TYPESCRIPT]:
            # Look for npm packages
            if re.search(r'\brequire\s*\(\s*[\'"](express|axios|lodash)[\'"]', code):
                info.has_dependencies = True
                info.packages = ['express', 'axios']  # Example

        # Generate cache key from dependencies
        if info.packages:
            dep_str = ','.join(sorted(info.packages))
            info.cache_key = hashlib.md5(dep_str.encode()).hexdigest()[:8]

        return info

    def install_dependencies(
        self,
        dependency_info: DependencyInfo,
        language: Language,
        container_name: str
    ) -> bool:
        """Install dependencies for code execution."""
        if not dependency_info.has_dependencies or not dependency_info.packages:
            return True

        config = self.get_config(language)
        if not config.install_command:
            return True

        # Check cache first
        cache_path = None
        if dependency_info.cache_key:
            cache_path = self.cache_dir / f"{language.value}_{dependency_info.cache_key}"
            if cache_path.exists():
                # Use cached dependencies
                return True

        try:
            # Create a temporary container to install dependencies
            install_config = ContainerConfig(
                image=config.image,
                command=config.install_command + dependency_info.packages,
                memory_limit="512m",
                cpu_limit="1.0",
                network_mode="bridge",  # Need network for downloading packages
                read_only=False,  # Need to write for installations
                tmpfs_size="200m",
            )

            # For some languages, we need to copy dependency files
            if config.dependency_file:
                # Create a temporary dependency file
                with tempfile.NamedTemporaryFile(mode='w', suffix=config.dependency_file, delete=False) as f:
                    if language in [Language.PYTHON, Language.PYTHON3]:
                        f.write('\n'.join(dependency_info.packages))
                    elif language in [Language.JAVASCRIPT, Language.TYPESCRIPT]:
                        f.write('{"dependencies": {' + ','.join([f'"{pkg}": "latest"' for pkg in dependency_info.packages]) + '}}')
                    dep_file_path = f.name

                install_config.volumes = {dep_file_path: f"/tmp/{config.dependency_file}"}
                install_config.command = config.install_command

            result = self.docker_manager.run_container(
                install_config,
                f"{container_name}_deps",
                timeout=120  # 2 minutes for dependency installation
            )

            success = result.success

            # Cache successful installations
            if success and cache_path:
                cache_path.touch()

            # Cleanup temp files
            if 'dep_file_path' in locals():
                os.unlink(dep_file_path)

            return success

        except Exception as e:
            print(f"Error installing dependencies: {e}")
            return False

    def prepare_execution_environment(
        self,
        code: str,
        language: Language,
        container_name: str
    ) -> Tuple[LanguageConfig, DependencyInfo]:
        """Prepare the execution environment with dependencies."""
        config = self.get_config(language)
        dep_info = self.analyze_dependencies(code, language)

        if dep_info.has_dependencies:
            self.install_dependencies(dep_info, language, container_name)

        return config, dep_info