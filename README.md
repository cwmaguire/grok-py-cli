# Grok CLI (Python Implementation)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://badge.fury.io/py/grok-py.svg)](https://badge.fury.io/py/grok-py)

A powerful, AI-powered terminal assistant built in Python. This is a Python implementation of [Grok CLI](https://github.com/superagent-ai/grok-cli), featuring a rich set of tools, MCP (Model Context Protocol) integration, and a beautiful terminal user interface.

![Grok CLI Demo](https://raw.githubusercontent.com/superagent-ai/grok-cli/main/assets/demo.gif)

## ✨ Features

- **Conversational AI**: Natural language interface powered by Grok API
- **Rich Tool Ecosystem**: 25+ built-in tools for file operations, system management, development, and more
- **MCP Integration**: Support for Model Context Protocol servers (GitHub, Linear, etc.)
- **Beautiful UI**: Rich terminal interface with syntax highlighting, markdown rendering, and interactive chat
- **Cross-Platform**: Works on Linux, macOS, and Windows
- **Secure**: Sandboxed code execution, path validation, and safe network operations

## 🛠️ Core Capabilities

### File Operations
- View, create, and edit files with precision
- Search across files and content
- Advanced text replacement with fuzzy matching

### System Management
- Execute shell commands safely
- Package management (apt)
- Systemd service control
- Network diagnostics and monitoring
- Disk usage analysis and cleanup

### Development Tools
- Safe code execution in Docker containers (Python, JavaScript, Java, C++, Go, Rust, Bash)
- Web search for current information
- Todo list management with visual progress tracking
- GitHub integration

### AI-Powered Features
- Context-aware conversations
- Tool calling and execution
- Custom instructions support
- Multiple Grok models (grok-code-fast-1, grok-3, grok-vision-beta)

## 📦 Installation

### Prerequisites
- Python 3.10 or higher
- A Grok API key from [xAI](https://x.ai/)

### Install from PyPI
```bash
pip install grok-py
```

### Install from Source
```bash
git clone https://github.com/superagent-ai/grok-cli.git
cd grok-cli
pip install -e .
```

### Using UV (Recommended)
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync

# Run grok-py
uv run grok-py --help
```

## ⚙️ Configuration

### API Key Setup
Set your Grok API key as an environment variable:

```bash
export GROK_API_KEY="your-api-key-here"
```

Or create a `.env` file in your project directory:
```
GROK_API_KEY=your-api-key-here
```

### Optional Environment Variables
- `GROK_MODEL`: Default model (default: grok-code-fast-1)
- `GROK_TEMPERATURE`: Response creativity (default: 0.7)
- `GROK_MAX_TOKENS`: Maximum response tokens
- `TAVILY_API_KEY`: For web search functionality
- `GITHUB_TOKEN`: For GitHub integration

## 🚀 Usage

### Basic Chat
Start an interactive chat session:
```bash
grok-py chat
```

Send a single message:
```bash
grok-py chat "Hello, can you help me with Python?"
```

### Advanced Chat Options
```bash
# Use a specific model
grok-py chat --model grok-3

# Adjust creativity
grok-py chat --temperature 0.9

# Limit response length
grok-py chat --max-tokens 1000

# Mock mode for testing (no API calls)
grok-py chat --mock
```

### MCP (Model Context Protocol) Integration

MCP allows Grok to use external tools and services. Configure MCP servers to extend functionality:

#### List Available Tools
```bash
grok-py mcp list-tools
```

#### Add an MCP Server
```bash
# Add a stdio-based server
grok-py mcp add-server my-server --command python --args path/to/server.py

# Add an HTTP-based server
grok-py mcp add-server my-http-server --url http://localhost:3000
```

#### Manage MCP Servers
```bash
# List configured servers
grok-py mcp list-servers

# Remove a server
grok-py mcp remove-server my-server
```

### Interactive Mode Features
- **F1**: Toggle between chat and command modes
- **Multi-line input**: Enter complex commands
- **Syntax highlighting**: Code and responses
- **Markdown rendering**: Rich text formatting
- **Tool execution**: Automatic tool calling with user confirmation

### Example Interactions

**File Operations:**
```
You: Create a new Python file called hello.py with a simple hello world function

Grok: I'll create the hello.py file for you.

[File created: hello.py]
```

**System Commands:**
```
You: Check the disk usage of my home directory

Grok: I'll run a disk usage check on your home directory.

[Running: du -sh ~]
1.2G    /home/user
```

**Code Execution:**
```
You: Run this Python code: print("Hello from Grok!")

Grok: I'll execute that Python code safely in a Docker container.

[Code execution result]
Hello from Grok!
```

## 🛠️ Available Tools

Grok CLI comes with a comprehensive set of built-in tools for various tasks:

### File Operations
- **File Editor**: View, create, and edit files with precision text replacement
- **Search**: Unified search across files and content using ripgrep
- **Archive**: Handle compressed files (zip, tar, etc.)

### System Management
- **Bash**: Execute shell commands safely
- **Apt**: Ubuntu/Debian package management (install, remove, update)
- **Systemctl**: Systemd service management (start, stop, restart services)
- **Disk**: Disk usage monitoring and cleanup suggestions
- **Network**: Network diagnostics (ping, traceroute, interfaces, connections)

### Development & Productivity
- **Code Execution**: Safe execution in Docker containers
  - Languages: Python, JavaScript, Java, C++, Go, Rust, Bash
- **Web Search**: Search the web using Tavily API
- **GitHub**: Repository management and operations
- **Todo**: Create and manage task lists with visual progress
- **Version Control**: Git operations and repository management

### Utilities
- **Calendar**: Date and time operations
- **Email**: Email handling capabilities
- **News**: Fetch news using NewsAPI
- **Weather**: Weather information and forecasts
- **Database**: Database operations (PostgreSQL, MySQL)
- **Integrity**: File integrity checking

### MCP Tools
When MCP servers are configured, additional tools become available:
- GitHub integration tools
- Linear (project management) tools
- Custom MCP server tools

All tools include proper error handling, user confirmation for destructive operations, and are designed with security in mind.

## ⚙️ Advanced Configuration

### MCP Server Configuration

MCP servers extend Grok's capabilities. Configuration is stored in `~/.config/grok-cli/mcp_config.yaml`.

Example configuration file:
```yaml
servers:
  # GitHub MCP server
  github:
    type: stdio
    command: npx
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "your-github-token"
    timeout: 30.0
    max_retries: 3

  # HTTP-based MCP server
  my-api-server:
    type: http
    url: "http://localhost:3001"
    timeout: 60.0
    max_retries: 5

  # Custom stdio server
  filesystem:
    type: stdio
    command: python
    args: ["/path/to/filesystem_server.py"]
    timeout: 30.0
```

### Custom Instructions

Create a custom instructions file at `~/.config/grok-cli/custom_instructions.txt`:

```
You are Grok, a helpful AI assistant. When writing code, prefer Python 3.10+ features and follow PEP 8 style guidelines. Always explain your reasoning before taking actions.
```

### Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `GROK_API_KEY` | Your Grok API key | Required |
| `GROK_MODEL` | Default model to use | `grok-code-fast-1` |
| `GROK_TEMPERATURE` | Response creativity (0.0-2.0) | `0.7` |
| `GROK_MAX_TOKENS` | Maximum response tokens | `None` |
| `TAVILY_API_KEY` | For web search functionality | Optional |
| `GITHUB_TOKEN` | For GitHub integration | Optional |
| `GROK_CLI_LOG_LEVEL` | Logging level | `INFO` |
| `GROK_CLI_CONFIG_DIR` | Configuration directory | `~/.config/grok-cli` |

### Docker Configuration

For code execution, ensure Docker is installed and running. The tool automatically manages containers for safe code execution.

## 🧑‍💻 Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/superagent-ai/grok-cli.git
cd grok-cli

# Using UV (recommended)
uv sync
uv run pre-commit install

# Or using pip
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .[dev]
pre-commit install
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=grok_py --cov-report=html

# Run specific test categories
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/acceptance/
```

### Code Quality

```bash
# Format code
uv run black grok_py tests
uv run isort grok_py tests

# Lint code
uv run flake8 grok_py tests
uv run mypy grok_py

# Run pre-commit hooks
uv run pre-commit run --all-files
```

### Building Documentation

```bash
# Build Sphinx documentation
uv run sphinx-build docs docs/_build/html
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and add tests
4. Run the test suite: `uv run pytest`
5. Format and lint: `uv run black . && uv run isort . && uv run flake8 .`
6. Commit your changes: `git commit -m "Add your feature"`
7. Push to the branch: `git push origin feature/your-feature`
8. Create a Pull Request

### Architecture Overview

```
grok_py/
├── cli.py              # Main CLI application
├── agent/              # Core AI agent logic
│   ├── grok_agent.py   # Main agent
│   └── tool_manager.py # Tool orchestration
├── tools/              # Tool implementations
├── ui/                 # Terminal user interface
├── grok/               # Grok API client
├── mcp/                # MCP protocol support
└── utils/              # Utilities and configuration
```

### Adding New Tools

1. Create a new tool class in `grok_py/tools/`
2. Inherit from `BaseTool` in `grok_py/tools/base.py`
3. Implement the required methods
4. Add the tool to the tool registry
5. Write comprehensive tests

### Performance Benchmarks

The project includes performance benchmarks to ensure optimal performance:

- Response time <2 seconds
- Memory usage <100MB baseline, <500MB with MCP
- Handle files up to 10MB
- Concurrent tool execution support

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **xAI** for the Grok API
- **Textualize** for the Rich library
- **The MCP Community** for the Model Context Protocol specification
- **Original Grok CLI Team** for the inspiration and TypeScript implementation

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/superagent-ai/grok-cli/issues)
- **Discussions**: [GitHub Discussions](https://github.com/superagent-ai/grok-cli/discussions)
- **Documentation**: [Read the Docs](https://grok-cli.readthedocs.io/)

---

<p align="center">
  <em>Built with ❤️ by the Grok CLI Team</em>
</p>