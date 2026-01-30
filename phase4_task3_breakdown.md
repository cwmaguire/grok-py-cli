Implement Phase 4, Task 3: Deep API Integrations for the Grok CLI Python project. This task involves creating comprehensive external API integrations to enhance the CLI's functionality with real-world data access and services.

    ## Task Overview

    Create a suite of API integration tools that provide access to external services, enabling the Grok agent to interact with web APIs for enhanced capabilities. Each tool should follow the established tool framework pattern with proper
    error handling, authentication, and rate limiting.

    ## Required Tools to Implement

    ### 1. GitHub API Tool (tools/github.py)

        * Repository operations: create, clone, fork, delete
        * Issue management: create, update, close, comment
        * Pull request operations: create, review, merge
        * Code search and file retrieval
        * Authentication via GitHub Personal Access Tokens
        * Rate limit handling and error recovery

    ### 2. Weather API Tool (tools/weather.py)

        * Current weather conditions by location
        * Weather forecasts (daily/hourly)
        * Multiple providers: OpenWeatherMap, WeatherAPI
        * Location geocoding and timezone handling
        * Data formatting for CLI display

    ### 3. News API Tool (tools/news.py)

        * Real-time news aggregation from multiple sources
        * Topic-based and keyword search functionality
        * Source credibility filtering
        * Article summarization capabilities
        * Caching for performance optimization

    ### 4. Database Tool (tools/database.py)

        * Support for SQLite, PostgreSQL, MySQL
        * Safe SQL query execution with injection prevention
        * Schema inspection and table operations
        * Connection pooling and transaction management
        * Result formatting for CLI output

    ### 5. Email Tool (tools/email.py)

        * SMTP/IMAP integration for email operations
        * Send emails with attachments
        * Receive and parse emails
        * Email filtering and search
        * Secure authentication (OAuth preferred)

    ### 6. Calendar Tool (tools/calendar.py)

        * Integration with Google Calendar and Outlook
        * Event CRUD operations (create, read, update, delete)
        * Scheduling and time zone management
        * Meeting invitations and attendee management
        * Calendar sharing and permissions

    ### 7. Social Media Tool (tools/social.py)

        * Twitter/X API integration
        * Post creation and management
        * User timeline and interaction analysis
        * Trend monitoring and analytics
        * Rate limiting and authentication handling

    ### 8. Financial Data Tool (tools/finance.py)

        * Real-time stock prices and market data
        * Cryptocurrency information and tracking
        * Portfolio management capabilities
        * Financial news aggregation
        * Chart generation and technical analysis

    ## Implementation Requirements

    ### Architecture Guidelines

        * Each tool must inherit from the base tool classes in `tools/base.py`
        * Implement proper async support where beneficial
        * Use configuration management for API keys and settings
        * Include comprehensive error handling and logging
        * Add rate limiting and retry logic for API calls
        * Provide both synchronous and asynchronous execution modes

    ### Security Considerations

        * Never expose API keys in code or logs
        * Implement proper authentication flows (OAuth where available)
        * Validate all inputs to prevent injection attacks
        * Use HTTPS for all API communications
        * Implement request/response validation

    ### Testing and Documentation

        * Create unit tests for each tool with mocked API responses
        * Include integration tests for actual API calls (with caution)
        * Provide usage examples and API documentation
        * Add tool-specific help and command-line options

    ### Performance Optimizations

        * Implement caching for frequently accessed data
        * Use connection pooling for database operations
        * Batch API requests where possible
        * Optimize data structures for CLI output formatting

    Start by implementing the GitHub API tool as it's most relevant to development workflows, then proceed with the other tools. Ensure all tools integrate seamlessly with the existing tool manager and CLI framework.

    Use the existing project structure and follow the patterns established in Phase 1 and 2 implementations. Focus on robust error handling, comprehensive logging, and user-friendly output formatting.
