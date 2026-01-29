# Grok CLI Development Makefile

.PHONY: help install dev-install test lint format clean build docs serve-docs

# Default target
help:
	@echo "Available commands:"
	@echo "  install      - Install the package in development mode"
	@echo "  dev-install  - Install with development dependencies"
	@echo "  test         - Run the test suite"
	@echo "  lint         - Run linting tools (black, isort, flake8, mypy)"
	@echo "  format       - Format code with black and isort"
	@echo "  clean        - Clean up build artifacts and cache files"
	@echo "  build        - Build the package"
	@echo "  docs         - Build documentation"
	@echo "  serve-docs   - Serve documentation locally"
	@echo "  activate     - Show command to activate virtual environment"

# Install the package in development mode
install:
	uv pip install -e .

# Install with development dependencies
dev-install:
	uv pip install -e .[dev,test,docs]

# Run tests
test:
	uv run pytest

# Run linting
lint:
	uv run black --check grok_py tests
	uv run isort --check-only grok_py tests
	uv run flake8 grok_py tests
	uv run mypy grok_py

# Format code
format:
	uv run black grok_py tests
	uv run isort grok_py tests

# Clean up
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .venv/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build the package
build:
	uv build

# Build documentation
docs:
	uv run sphinx-build -b html docs docs/_build/html

# Serve documentation locally
serve-docs:
	cd docs/_build/html && python -m http.server 8000

# Show activation command
activate:
	@echo "To activate the virtual environment, run:"
	@echo "  source .venv/bin/activate"