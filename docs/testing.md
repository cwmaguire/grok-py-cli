# Testing Guide

This guide provides comprehensive information about the testing suite for Grok CLI Python implementation.

## Overview

The project uses pytest for testing with a comprehensive test suite covering:
- **Unit Tests**: Individual function and method testing
- **Integration Tests**: Component interaction testing
- **System Tests**: End-to-end workflow testing
- **Acceptance Tests**: User scenario validation

## Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
├── integration/            # Integration tests for component interactions
├── system/                 # System tests for complete workflows
├── acceptance/             # Acceptance tests for user scenarios
├── fixtures/               # Shared test fixtures and mock data
├── conftest.py            # Pytest configuration and fixtures
└── __init__.py
```

## Running Tests

### Prerequisites

Install test dependencies:
```bash
# Using uv (recommended)
uv sync --group test

# Or using pip
pip install -e ".[test]"
```

### Run All Tests

```bash
# Run complete test suite
pytest

# Run with coverage
pytest --cov=grok_py --cov-report=term-missing --cov-report=html

# Run specific test types
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m system        # System tests only
pytest -m acceptance    # Acceptance tests only
```

### Run Specific Test Files

```bash
# Run specific test file
pytest tests/unit/test_cli.py

# Run tests matching pattern
pytest -k "test_file" -v

# Run tests in specific directory
pytest tests/unit/
```

### Test Options

```bash
# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Show coverage in terminal
pytest --cov=grok_py --cov-report=term

# Generate HTML coverage report
pytest --cov=grok_py --cov-report=html

# Run tests in parallel (requires pytest-xdist)
pytest -n auto
```

## Test Categories

### Unit Tests (`tests/unit/`)

Test individual functions, methods, and classes with mocked dependencies.

**Examples:**
- Tool execution methods
- Utility functions
- Configuration management
- CLI argument parsing

### Integration Tests (`tests/integration/`)

Test interactions between components with real dependencies where safe.

**Examples:**
- Tool workflows with actual file system
- API integrations with mock servers
- Cross-component data flow

### System Tests (`tests/system/`)

Test complete application workflows from start to finish.

**Examples:**
- Development workflows (create, edit, run, debug)
- System administration tasks
- Multi-tool interactions

### Acceptance Tests (`tests/acceptance/`)

Validate real-world user scenarios and requirements.

**Examples:**
- Performance validation
- Error handling scenarios
- User journey validation

## Coverage Requirements

### Coverage Goals

- **Overall Coverage**: >90%
- **Core Modules**: >95%
- **New Code**: >90%

### Coverage Reporting

```bash
# Terminal report
pytest --cov=grok_py --cov-report=term-missing

# HTML report (opens in browser)
pytest --cov=grok_py --cov-report=html && open htmlcov/index.html

# XML report for CI
pytest --cov=grok_py --cov-report=xml
```

### Coverage Configuration

Coverage settings are configured in `pytest.ini`:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --strict-markers --cov=grok_py --cov-report=term-missing
markers =
    unit: Unit tests
    integration: Integration tests
    system: System tests
    acceptance: Acceptance tests
    slow: Slow running tests
```

## Writing Tests

### Test Naming Conventions

- Files: `test_*.py`
- Classes: `Test*`
- Methods: `test_*`
- Fixtures: Use descriptive names

### Test Organization

```python
import pytest
from unittest.mock import Mock, patch

class TestMyComponent:
    """Test suite for MyComponent."""

    @pytest.fixture
    def sample_data(self):
        """Fixture providing sample test data."""
        return {"key": "value"}

    def test_basic_functionality(self):
        """Test basic functionality."""
        # Arrange
        component = MyComponent()

        # Act
        result = component.do_something()

        # Assert
        assert result.success is True

    @patch('mymodule.external_dependency')
    def test_with_mock(self, mock_dependency):
        """Test with mocked external dependency."""
        mock_dependency.return_value = Mock(success=True)

        component = MyComponent()
        result = component.do_something()

        assert result.success is True
        mock_dependency.assert_called_once()
```

### Mocking Guidelines

- Mock external APIs and services
- Mock file system operations for unit tests
- Use fixtures for common mock objects
- Verify mock interactions where relevant

### Test Data Management

- Use `tests/fixtures/` for shared test data
- Create temporary files/directories for file operations
- Clean up after tests automatically

## CI/CD Integration

### GitHub Actions

Tests run automatically on:
- Push to main branch
- Pull requests
- Scheduled runs

### CI Configuration

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v1
      - run: uv sync --group test
      - run: pytest --cov=grok_py --cov-report=xml
      - uses: codecov/codecov-action@v3
```

### Coverage Upload

Coverage reports are automatically uploaded to Codecov for tracking.

## Maintenance Guidelines

### Adding New Tests

1. Identify the appropriate test category (unit/integration/system/acceptance)
2. Create test file in correct directory
3. Follow naming conventions
4. Add necessary fixtures and mocks
5. Ensure test coverage for new code

### Test Maintenance

- Keep tests updated when code changes
- Remove obsolete tests
- Refactor tests for clarity
- Review test performance regularly

### Debugging Failing Tests

```bash
# Run with detailed output
pytest -v -s

# Debug specific test
pytest --pdb tests/unit/test_mycomponent.py::TestMyComponent::test_method

# Run tests in isolation
pytest -k "test_method" --no-cov
```

## Performance Considerations

### Test Speed

- Unit tests should run in <100ms each
- Integration tests <1s each
- System tests <10s each
- Full suite <5 minutes

### Parallel Execution

Use pytest-xdist for parallel test execution:

```bash
# Install
pip install pytest-xdist

# Run in parallel
pytest -n auto
```

## Troubleshooting

### Common Issues

**Import Errors:**
- Ensure test dependencies are installed
- Check Python path includes project root

**Mock Errors:**
- Verify mock targets are correct
- Check patch decorators are applied properly

**Coverage Issues:**
- Ensure all new code has corresponding tests
- Check coverage configuration excludes appropriate files

**CI Failures:**
- Check CI logs for specific errors
- Verify environment setup in CI

### Getting Help

- Check existing test examples
- Review pytest documentation
- Ask in project discussions

## Test Maintenance Guidelines

### Adding New Tests

1. **Follow Naming Conventions:**
   - Test files: `test_*.py`
   - Test classes: `Test*`
   - Test methods: `test_*`

2. **Structure Tests Properly:**
   - Use descriptive test names
   - Include docstrings explaining test purpose
   - Group related tests in classes

3. **Mock External Dependencies:**
   - Use `pytest-mock` or `unittest.mock` for external calls
   - Avoid real network calls in unit tests
   - Mock file system operations appropriately

### Updating Tests

1. **When Code Changes:**
   - Update affected tests immediately
   - Check for breaking changes in APIs
   - Update mocks if interfaces change

2. **Refactoring Tests:**
   - Keep tests readable and maintainable
   - Remove duplicate code with fixtures
   - Update test documentation

### Coverage Maintenance

1. **Monitor Coverage:**
   - Run coverage reports regularly
   - Identify untested code paths
   - Add tests for new features

2. **Coverage Goals:**
   - Maintain >90% overall coverage
   - Focus on critical business logic
   - Exclude generated/config code if appropriate

### Performance Considerations

1. **Test Execution Time:**
   - Keep individual tests fast (<1s)
   - Use appropriate test markers for slow tests
   - Parallelize where possible

2. **Resource Usage:**
   - Clean up test fixtures
   - Avoid memory leaks in tests
   - Use temporary files/directories appropriately

## Success Criteria

- All tests pass consistently
- >90% code coverage achieved
- Tests run in <5 minutes on CI
- Clear documentation for running and maintaining tests
- Integration with CI/CD pipeline