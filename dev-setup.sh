#!/bin/bash
# Development setup script for Grok CLI

set -e

echo "🚀 Setting up Grok CLI development environment with uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install uv first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ uv is installed"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    uv venv
else
    echo "✅ Virtual environment already exists"
fi

# Install dependencies
echo "📦 Installing dependencies..."
uv pip install -e .[dev,test,docs]

# Setup pre-commit hooks
if [ -f ".pre-commit-config.yaml" ]; then
    echo "🔧 Setting up pre-commit hooks..."
    uv run pre-commit install
fi

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "To activate the virtual environment:"
echo "  source .venv/bin/activate"
echo ""
echo "Or use uv run for commands:"
echo "  uv run python -m grok_py --help"
echo "  uv run pytest"
echo "  uv run black grok_py"
echo ""
echo "Available make commands:"
echo "  make help         - Show all available commands"
echo "  make test         - Run tests"
echo "  make lint         - Run linting"
echo "  make format       - Format code"
echo "  make clean        - Clean up artifacts"