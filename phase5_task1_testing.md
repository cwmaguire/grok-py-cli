 You are an expert Python developer and testing specialist. Your task is to implement a comprehensive testing suite for the Grok CLI Python project as part of Phase 5, Task 1. This involves creating thorough tests to ensure code
    quality, reliability, and maintainability.

        ## Project Context
        - This is a Python implementation of Grok CLI, a terminal-based AI assistant
        - The project uses modern Python (3.8+), typer for CLI, and various tools for different operations
        - Key components include: CLI interface, agent system, MCP integration, tools (file ops, system, web, etc.), and utilities
        - This project uses uv for Python dependencies and virtual
          environments; do not update the system Python dependencies
          with raw pip calls.

        ## Testing Objectives
        - Achieve >90% test coverage across all modules
        - Ensure all tools and core functionality work correctly
        - Validate error handling, edge cases, and performance
        - Test both synchronous and asynchronous operations
        - Verify integration between components

        ## Required Testing Structure

        ### 1. Unit Testing (`tests/unit/`)
        Create individual tests for functions and methods:
        - **Core Modules**: Test CLI parsing, agent logic, configuration management
        - **Tools**: Test each tool's execute methods with mocked dependencies
        - **Utilities**: Test helper functions, token counting, settings management
        - **Base Classes**: Test tool framework, result handling, parameter validation

        ### 2. Integration Testing (`tests/integration/`)
        Test component interactions and workflows:
        - **Tool Execution**: End-to-end tool execution with real dependencies where safe
        - **API Integrations**: Test external APIs with mock servers (GitHub, web search, etc.)
        - **File Operations**: Test file manipulation workflows
        - **Code Execution**: Test Docker-based code execution environment

        ### 3. System Testing (`tests/system/`)
        Test the complete application:
        - **Full Workflows**: Complete user scenarios from CLI input to output
        - **Cross-Platform**: Test on Linux/macOS/Windows (as applicable)
        - **Resource Usage**: Memory, CPU, and concurrent operation testing
        - **Configuration**: Test different configuration scenarios

        ### 4. Acceptance Testing (`tests/acceptance/`)
        Validate real-world usage:
        - **User Scenarios**: Test common use cases and workflows
        - **Performance**: Validate against response time requirements
        - **Compatibility**: Ensure compatibility with existing patterns

        ## Technical Requirements

        ### Testing Framework
        - Use `pytest` as the primary testing framework
        - Configure `pytest.ini` with coverage settings
        - Use `pytest-asyncio` for async test support
        - Set up test markers for different test types (unit, integration, slow, etc.)

        ### Mocking and Fixtures
        - Use `pytest-mock` or `unittest.mock` for external dependencies
        - Create fixtures for common test data and mocked services
        - Mock API responses, file system operations, and network calls
        - Use `responses` for HTTP API mocking

        ### Test Organization
        - Follow `tests/test_*.py` naming convention
        - Mirror source code structure in test directories
        - Use descriptive test names and docstrings
        - Include test data and fixtures in `tests/fixtures/`

        ### Coverage and Quality
        - Configure `coverage.py` for detailed reporting
        - Set up CI/CD integration with coverage requirements
        - Include static analysis with `flake8`, `mypy`, `black`
        - Add performance benchmarks using `pytest-benchmark`

        ## Implementation Steps

        1. **Setup Testing Infrastructure**
           - Install testing dependencies in `pyproject.toml`
           - Configure `pytest.ini` and `setup.cfg`
           - Set up test directory structure
           - Create base test fixtures and utilities

        2. **Implement Unit Tests**
           - Start with core modules (base classes, utilities)
           - Test tools with comprehensive mocking
           - Cover error conditions and edge cases
           - Achieve high coverage for critical paths

        3. **Implement Integration Tests**
           - Test tool execution workflows
           - Mock external APIs appropriately
           - Test cross-component interactions
           - Validate data flow between modules

        4. **Implement System Tests**
           - Create full application tests
           - Test CLI interface end-to-end
           - Validate configuration and environment handling
           - Test concurrent operations

        5. **Implement Acceptance Tests**
           - Define user personas and scenarios
           - Test real-world usage patterns
           - Validate performance requirements
           - Include usability testing

        6. **Quality Assurance**
           - Run full test suite with coverage reporting
           - Fix any failing tests and coverage gaps
           - Add documentation for test setup and running
           - Create test maintenance guidelines

        ## Success Criteria
        - All tests pass consistently
        - >90% code coverage achieved
        - Tests run in <5 minutes on CI
        - Comprehensive mocking prevents external dependencies
        - Clear documentation for running and maintaining tests
        - Integration with CI/CD pipeline

        Begin by analyzing the current codebase structure, then implement the testing infrastructure and start with unit tests for the most critical components.
