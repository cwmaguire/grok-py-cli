# Grok CLI Python Implementation

[![CI](https://github.com/superagent-ai/grok-cli/workflows/CI/badge.svg)](https://github.com/superagent-ai/grok-cli/actions)
[![PyPI](https://img.shields.io/pypi/v/grok-py.svg)](https://pypi.org/project/grok-py/)
[![Python Version](https://img.shields.io/pypi/pyversions/grok-py.svg)](https://pypi.org/project/grok-py/)
[![License](https://img.shields.io/pypi/l/grok-py.svg)](https://github.com/superagent-ai/grok-cli/blob/main/LICENSE)

A Python implementation of the Grok CLI tool, replicating the functionality of the existing TypeScript-based grok-cli project with Python's ecosystem advantages.

## Features

- 🤖 **Conversational AI Interface**: Natural language interface powered by Grok-3 API
- 🛠️ **Tool System**: Support for 13+ tools including file operations, system management, development utilities, and network diagnostics
- 🎨 **Beautiful Terminal UI**: Rich terminal interface with real-time updates using Rich library
- 🔧 **Extensible Architecture**: Plugin-based tool system with MCP (Model Context Protocol) support
- 🌐 **Web Search Integration**: Built-in web search using Tavily API
- 🐳 **Code Execution Sandbox**: Safe code execution in isolated Docker containers
- 📊 **Task Management**: Built-in todo system for planning and tracking tasks

## Installation

### Prerequisites

This project uses [uv](https://github.com/astral-sh/uv) for fast, isolated Python package management. Install uv first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### From PyPI

```bash
uv pip install grok-py
```

### From Source

```bash
git clone https://github.com/superagent-ai/grok-cli.git
cd grok-cli
uv pip install -e .
```

### Development Setup

The easiest way to set up the development environment is using the provided setup script:

```bash
git clone https://github.com/superagent-ai/grok-cli.git
cd grok-cli
./dev-setup.sh
```

Or manually:

```bash
git clone https://github.com/superagent-ai/grok-cli.git
cd grok-cli
uv venv
uv pip install -e .[dev,test,docs]
uv run pre-commit install
```

### Using the Virtual Environment

You can either activate the virtual environment:

```bash
source .venv/bin/activate
python -m grok_py --help
```

Or use `uv run` to execute commands without activation:

```bash
uv run python -m grok_py --help
uv run pytest
uv run black grok_py
```

### Development Commands

Use the provided Makefile for common development tasks:

```bash
make help         # Show all available commands
make test         # Run tests
make lint         # Run linting
make format       # Format code
make clean        # Clean up artifacts
```

## Quick Start

1. **Set up your API key**:
   ```bash
   export GROK_API_KEY="your-grok-api-key"
   export TAVILY_API_KEY="your-tavily-api-key"  # Optional, for web search
   ```

2. **Start chatting**:
   ```bash
   grok-py chat "Hello, can you help me with Python development?"
   ```

3. **Use tools**:
   ```bash
   grok-py chat "List the files in the current directory"
   ```

## Usage

### Basic Commands

```bash
# Chat with Grok
grok-py chat "Your message here"

# Get version information
grok-py version

# Show help
grok-py --help
```

### Configuration

Create a `.env` file in your project directory:

```env
GROK_API_KEY=your-grok-api-key
TAVILY_API_KEY=your-tavily-api-key
MORPH_API_KEY=your-morph-api-key
```

## Available Tools

### File Operations
- **Text Editor**: View, create, and edit files
- **Morph Editor**: High-speed code editing with advanced diffing
- **Search**: Unified search across files and content

### System Tools
- **Bash**: Execute shell commands
- **Apt**: Ubuntu package management
- **Systemctl**: Systemd service management
- **Disk**: Disk usage monitoring and cleanup
- **Network**: Network diagnostics (ping, traceroute, etc.)

### Development Tools
- **Code Execution**: Safe code execution in Docker containers
- **Web Search**: Web search using Tavily API
- **Todo**: Task planning and tracking

## Development

### Project Structure

```
grok_py/
├── __main__.py          # CLI entry point
├── cli.py               # Main CLI application
├── agent/               # Core agent logic
│   ├── grok_agent.py    # Main agent class
│   └── tool_manager.py  # Tool orchestration
├── tools/               # Individual tool implementations
├── ui/                  # Terminal UI components
├── grok/                # Grok API integration
├── mcp/                 # MCP integration
└── utils/               # Utilities
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=grok_py

# Run linting
uv run black grok_py tests
uv run isort grok_py tests
uv run flake8 grok_py tests
uv run mypy grok_py

# Or use make commands
make test
make lint
make format
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## Documentation

Full documentation is available at [https://grok-cli.readthedocs.io/](https://grok-cli.readthedocs.io/)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Based on the original [grok-cli](https://github.com/superagent-ai/grok-cli) TypeScript implementation
- Powered by [Grok](https://grok.x.ai/) from xAI
- Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal interfaces