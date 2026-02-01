"""Unit tests for CalendarTool."""

import pytest
from unittest.mock import patch, MagicMock
from grok_py.tools.calendar import CalendarTool, CalendarProvider
from grok_py.tools.base import ToolResult


class TestCalendarProvider:
    """Test CalendarProvider enum."""

    def test_enum_values(self):
        """Test CalendarProvider enum values."""
        assert CalendarProvider.GOOGLE == "google"
        assert CalendarProvider.OUTLOOK == "outlook"


class TestCalendarTool:
    """Test CalendarTool class."""

    def setup_method(self):
        """Set up test method."""
        with patch('grok_py.tools.calendar.os.makedirs'), \
             patch('grok_py.tools.calendar.os.path.exists', return_value=False), \
             patch('grok_py.tools.calendar.os.getenv', return_value=None):
            self.tool = CalendarTool()

    @patch('grok_py.tools.calendar.os.getenv')
    @patch('grok_py.tools.calendar.os.path.exists')
    @patch('grok_py.tools.calendar.os.makedirs')
    def test_init_no_credentials(self, mock_makedirs, mock_exists, mock_getenv):
        """Test CalendarTool initialization without credentials."""
        mock_getenv.return_value = None
        mock_exists.return_value = False

        tool = CalendarTool()

        assert tool.google_creds is None
        assert tool.outlook_token is None
        assert tool.google_service is None

    def test_execute_sync_unsupported_provider(self):
        """Test execute_sync with unsupported provider."""
        result = self.tool.execute_sync("list_events", provider="unsupported")

        assert result.success is False
        assert "Unsupported provider" in result.error

    @patch.object(CalendarTool, '_execute_google')
    def test_execute_sync_google(self, mock_execute_google):
        """Test execute_sync with Google provider."""
        mock_result = ToolResult(success=True, data={"events": []})
        mock_execute_google.return_value = mock_result

        result = self.tool.execute_sync("list_events", provider="google")

        mock_execute_google.assert_called_once_with("list_events")
        assert result == mock_result

    @patch.object(CalendarTool, '_execute_outlook')
    def test_execute_sync_outlook(self, mock_execute_outlook):
        """Test execute_sync with Outlook provider."""
        mock_result = ToolResult(success=True, data={"events": []})
        mock_execute_outlook.return_value = mock_result

        result = self.tool.execute_sync("list_events", provider="outlook")

        mock_execute_outlook.assert_called_once_with("list_events")
        assert result == mock_result

    def test_execute_sync_exception(self):
        """Test execute_sync with general exception."""
        with patch.object(self.tool, '_execute_google', side_effect=Exception("API error")):
            result = self.tool.execute_sync("list_events", provider="google")

        assert result.success is False
        assert result.error == "API error"

    def test_execute_google_no_service(self):
        """Test _execute_google without service."""
        self.tool.google_service = None

        result = self.tool._execute_google("list_events")

        assert result.success is False
        assert "Google Calendar not authenticated" in result.error

    def test_execute_google_unsupported_operation(self):
        """Test _execute_google with unsupported operation."""
        self.tool.google_service = MagicMock()

        result = self.tool._execute_google("unsupported_op")

        assert result.success is False
        assert "Unsupported Google Calendar operation" in result.error

    @patch.object(CalendarTool, '_google_list_events')
    def test_execute_google_list_events(self, mock_list_events):
        """Test _execute_google list_events operation."""
        self.tool.google_service = MagicMock()
        mock_result = ToolResult(success=True, data={"events": []})
        mock_list_events.return_value = mock_result

        result = self.tool._execute_google("list_events")

        mock_list_events.assert_called_once()
        assert result == mock_result

    def test_execute_outlook_no_token(self):
        """Test _execute_outlook without token."""
        self.tool.outlook_token = None

        result = self.tool._execute_outlook("list_events")

        assert result.success is False
        assert "Outlook access token not configured" in result.error

    @patch.object(CalendarTool, '_outlook_list_events')
    def test_execute_outlook_list_events(self, mock_list_events):
        """Test _execute_outlook list_events operation."""
        self.tool.outlook_token = "fake_token"
        mock_result = ToolResult(success=True, data={"events": []})
        mock_list_events.return_value = mock_result

        result = self.tool._execute_outlook("list_events")

        mock_list_events.assert_called_once()
        assert result == mock_result

    def test_execute_outlook_unsupported_operation(self):
        """Test _execute_outlook with unsupported operation."""
        self.tool.outlook_token = "fake_token"

        result = self.tool._execute_outlook("unsupported_op")

        assert result.success is False
        assert "Unsupported Outlook operation" in result.error

    @patch.object(CalendarTool, 'google_service')
    def test_google_list_events(self, mock_service):
        """Test _google_list_events method."""
        mock_events = {"items": [{"summary": "Test Event", "start": {"dateTime": "2024-01-01T10:00:00Z"}}]}
        mock_service.events.return_value.list.return_value.execute.return_value = mock_events

        result = self.tool._google_list_events(calendar_id="primary", max_results=10)

        assert result.success is True
        assert result.data["events"] == mock_events["items"]
        mock_service.events.return_value.list.assert_called_once_with(
            calendarId="primary",
            maxResults=10,
            singleEvents=True,
            orderBy="startTime"
        )

    @patch.object(CalendarTool, 'google_service')
    def test_google_create_event(self, mock_service):
        """Test _google_create_event method."""
        mock_event = {"summary": "New Event", "start": {"dateTime": "2024-01-01T10:00:00Z"}}
        mock_service.events.return_value.insert.return_value.execute.return_value = mock_event

        result = self.tool._google_create_event(
            calendar_id="primary",
            summary="New Event",
            start_time="2024-01-01T10:00:00Z",
            end_time="2024-01-01T11:00:00Z"
        )

        assert result.success is True
        assert result.data["event"] == mock_event

    @patch('grok_py.tools.calendar.requests.get')
    def test_outlook_list_events(self, mock_get):
        """Test _outlook_list_events method."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": [{"subject": "Test Event"}]}
        mock_get.return_value = mock_response

        headers = {"Authorization": "Bearer fake_token"}
        result = self.tool._outlook_list_events(headers, calendar_id="calendar_id")

        assert result.success is True
        assert result.data["events"] == [{"subject": "Test Event"}]
        mock_get.assert_called_once()

    def test_retry_api_call_success(self):
        """Test _retry_api_call with success."""
        def dummy_func(x):
            return x * 2

        result = self.tool._retry_api_call(dummy_func, x=5)

        assert result == 10

    @patch('grok_py.tools.calendar.time.sleep')
    def test_retry_api_call_retry(self, mock_sleep):
        """Test _retry_api_call with retry on failure."""
        call_count = 0
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary error")
            return "success"

        result = self.tool._retry_api_call(failing_func, max_retries=3)

        assert result == "success"
        assert call_count == 3
        assert mock_sleep.call_count == 2