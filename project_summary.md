# Project Summary: Grok CLI Python Implementation

## 1. Introduction and Objectives

This is a Python implementation of Grok CLI, a terminal-based AI assistant replicating the TypeScript-based grok-cli project (https://github.com/superagent-ai/grok-cli). The goal is to create a fully functional Python equivalent maintaining all core features while leveraging Python's ecosystem for better maintainability and extensibility.

Objectives:
- Full compatibility with Grok API
- Cross-platform support (Linux, macOS, Windows)
- Modern Python codebase with best practices

## 2. Core Features and Requirements

### Conversational AI Interface
- Natural language interface via Grok-3 API
- Real-time chat with streaming, context history, token management
- Custom instructions support

### Tool System
Replicates TypeScript tools:

#### File Operations
- Text Editor: View, create, edit files with string replacement
- Morph Editor: High-speed code editing (4,500+ tokens/sec, 98% accuracy)
- Search: Unified file/content search

#### System Tools
- Bash: Execute shell commands
- Apt: Ubuntu package management
- Systemctl: Systemd service management
- Disk: Usage monitoring and cleanup
- Network: Diagnostics (ping, traceroute, etc.)

#### Development Tools
- Code Execution: Safe execution in Docker (JS, Python, Java, C++, Go, Rust, Bash)
- Web Search: Tavily API for current info
- Todo: Task planning with visual progress

#### Utility
- Confirmation: User approval for operations

### User Interface
- Beautiful terminal UI with Rich library
- Chat interface, multiline input (F1 toggle), syntax highlighting, Markdown rendering
- Confirmation dialogs

### MCP Integration
- Support for MCP servers (Linear, GitHub, etc.)
- Dynamic tool loading

### Configuration
- Environment-based settings
- API keys, custom instructions, MCP configs

## 3. Architecture Overview

### Module Structure
```
grok_py/
├── __main__.py          # CLI entry
├── cli.py               # Main CLI app
├── agent/               # Core logic
│   ├── grok_agent.py    # Main agent
│   └── tool_manager.py  # Tool orchestration
├── tools/               # Tool implementations
│   ├── base.py          # Base tool class
│   ├── file_editor.py
│   ├── bash.py
│   └── ...
├── ui/                  # Terminal UI
│   ├── chat_interface.py
│   └── components/
├── grok/                # Grok API
│   ├── client.py
│   └── tools.py
├── mcp/                 # MCP client
└── utils/               # Utilities
    ├── token_counter.py
    ├── settings.py
    └── custom_instructions.py
```

### Key Classes
- GrokAgent: Manages conversation and tool execution
- Tool Base Classes: Abstract for tool types
- UI Manager: Terminal rendering
- Configuration Manager: Settings/API keys

## 4. Technical Requirements

### Python Version
- Minimum: 3.8+
- Recommended: 3.10+

### Dependencies
Core equivalents:
- CLI: typer
- UI: rich
- API: httpx, openai
- File ops: pathlib
- Markdown: rich
- Syntax: pygments
- Token: tiktoken
- Search: ripgrep
- Docker: docker-py
- Web: tavily-python

### Platform Support
- Primary: Linux (Ubuntu/Debian)
- Secondary: macOS, Windows
- Docker for sandboxing

### Performance
- Response <2s
- Memory <100MB baseline, <500MB with MCP
- Handle 10MB files
- Concurrent operations

## 5. Implementation Notes

### Migration
- Exact API compatibility
- Preserve tool schemas, errors, configs

### Enhancements
- Async/await for concurrency
- Full type hints
- Comprehensive testing with pytest
- Modern packaging (pyproject.toml)
- Auto-docs with Sphinx

### Security
- Secure API key handling
- Sandboxed code execution
- Path validation for files
- Safe network commands

## 6. Development and Deployment

### Setup
- Virtual env: venv or Poetry
- Testing: pytest with coverage
- Linting: black, isort, flake8, mypy
- CI/CD: GitHub Actions

### Installation
- pip install --user grok-py
- Local: pip install -e .
- Docker: Containerized

### Distribution
- PyPI
- GitHub Releases
- Docker Hub

## 7. Testing Requirements

### Objectives
- >90% coverage
- Validate tools, errors, async ops
- Integration and system tests

### Structure
- Unit: tests/unit/ - functions, tools with mocks
- Integration: tests/integration/ - workflows, APIs
- System: tests/system/ - full app, cross-platform
- Acceptance: tests/acceptance/ - user scenarios, performance

### Framework
- pytest with asyncio
- Mocking: pytest-mock, responses
- Coverage: coverage.py
- Benchmarks: pytest-benchmark

### Implementation Steps
1. Setup infrastructure (deps, config)
2. Unit tests (core, tools)
3. Integration (workflows)
4. System (full app)
5. Acceptance (scenarios)
6. QA (coverage, docs)

Success: All pass, >90% coverage, <5min CI

## 8. UV Best Practices

UV manages Python deps and venvs efficiently.

### Key Commands
- uv sync: Sync from pyproject.toml
- uv run <cmd>: Run in venv
- uv add/remove: Manage deps
- uv lock: Update lockfile
- uv venv: Create venv

### Practices
- Check uv --version; install if needed
- Use uv run for commands (e.g., uv run pytest)
- Sync after changes
- Specify Python version if needed
- Avoid raw pip
- For testing: uv run pytest -v

### Troubleshooting
- Failures: Check deps (uv sync), Python version
- Async issues: pytest-asyncio
- Patches: Verify import paths
- Performance: Sync once, reuse venv

Always use uv run for Python commands in this project.

## Development Notes and Troubleshooting

### Dependency Management
- Use `uv sync` to install base dependencies; for dev dependencies (including pytest), use `uv sync --extra dev`
- Do not use raw pip commands; stick to uv for all dependency operations
- If tests fail with ModuleNotFoundError for pytest or other dev tools, ensure dev extras are installed

### Testing Setup
- Tests are configured in `pytest.ini` with coverage and async support
- Acceptance tests use `@pytest.mark.acceptance` marker (may show warnings as unknown, but tests run fine)
- Tool classes require instantiation without arguments in tests; BaseTool.__init__ uses register_tool metadata for defaults
- File operation tools are in `grok_py.tools.file_tools`, not `file_editor`
- Error assertions in tests must match exact tool output strings (e.g., "Path does not exist" for missing files)

### Tool Instantiation
- Tools decorated with `@register_tool` can be instantiated with `ToolClass()` in tests, as __init__ pulls metadata from class attributes
- For production use, tools are registered via ToolManager.discover_tools()

### Common Command Failures
- `uv run pytest` failing: Install dev dependencies with `uv sync --extra dev`
- Import errors in tests: Check module paths (e.g., file_tools vs file_editor)
- Tool instantiation errors: Ensure BaseTool.__init__ has optional parameters with metadata fallbacks
- Assertion failures: Verify exact error message strings from tool implementations