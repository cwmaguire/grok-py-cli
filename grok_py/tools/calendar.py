"""Calendar tool for Google Calendar and Outlook integration with event management."""

import os
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum

import requests

try:
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    build = None
    Credentials = None
    Request = None
    InstalledAppFlow = None
    HttpError = Exception  # Fallback
    GOOGLE_AVAILABLE = False

from .base import SyncTool, ToolCategory, ToolResult


class CalendarProvider(str, Enum):
    """Calendar provider types."""
    GOOGLE = "google"
    OUTLOOK = "outlook"


class CalendarTool(SyncTool):
    """Tool for calendar operations with Google Calendar and Outlook integration.

    Supports CRUD operations on events, scheduling, time zone management,
    meeting invitations, attendee management, calendar sharing, and permissions.

    Authentication:
    - Google Calendar: Requires credentials.json in ~/.config/grok-cli/ and OAuth flow
    - Outlook: Requires OUTLOOK_ACCESS_TOKEN environment variable

    Examples:
        # List upcoming events
        tool.execute_sync("list_events", provider="google", max_results=5)

        # Create an event
        tool.execute_sync("create_event", provider="google",
                         summary="Meeting", start_time="2024-01-01T10:00:00Z",
                         end_time="2024-01-01T11:00:00Z", attendees=["user@example.com"])

        # Share calendar
        tool.execute_sync("share_calendar", provider="google", email="user@example.com", role="writer")
    """

    def __init__(self):
        super().__init__(
            name="calendar",
            description="Calendar integration for Google Calendar and Outlook with event CRUD operations, scheduling, and meeting management",
            category=ToolCategory.WEB
        )

        self.google_creds = None
        self.outlook_token = None
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize calendar service clients."""
        # Google Calendar setup
        self._setup_google_calendar()

        # Outlook setup
        self.outlook_token = os.getenv("OUTLOOK_ACCESS_TOKEN")
        self.outlook_client_id = os.getenv("OUTLOOK_CLIENT_ID")
        self.outlook_tenant_id = os.getenv("OUTLOOK_TENANT_ID")

    def _retry_api_call(self, func, max_retries: int = 3, backoff_factor: float = 0.5, **kwargs):
        """Retry API call with exponential backoff."""
        last_exception = None
        for attempt in range(max_retries):
            try:
                return func(**kwargs)
            except (HttpError, requests.RequestException) as e:
                last_exception = e
                if hasattr(e, 'resp') and e.resp.status in [429, 500, 502, 503, 504]:  # Rate limit or server errors
                    wait_time = backoff_factor * (2 ** attempt)
                    self.logger.warning(f"API call failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    # Don't retry for client errors (4xx except 429)
                    raise e
        raise last_exception

    def _setup_google_calendar(self):
        """Setup Google Calendar API client."""
        if not GOOGLE_AVAILABLE:
            self.google_service = None
            return
        creds = None
        token_path = os.path.expanduser("~/.config/grok-cli/google_token.json")
        creds_path = os.path.expanduser("~/.config/grok-cli/google_credentials.json")

        # Ensure config directory exists
        os.makedirs(os.path.dirname(token_path), exist_ok=True)

        # Load saved credentials
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, ['https://www.googleapis.com/auth/calendar'])

        # If credentials are invalid or don't exist, attempt refresh or auth
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    self.logger.warning(f"Failed to refresh Google credentials: {e}")
                    creds = None
            else:
                # Need to authenticate - check if credentials.json exists
                if os.path.exists(creds_path):
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            creds_path, ['https://www.googleapis.com/auth/calendar']
                        )
                        creds = flow.run_local_server(port=0)
                        # Save the credentials for the next run
                        with open(token_path, 'w') as token:
                            token.write(creds.to_json())
                    except Exception as e:
                        self.logger.error(f"Failed to authenticate with Google: {e}")
                        creds = None
                else:
                    self.logger.warning("Google credentials.json not found. Please download from Google Cloud Console and place at ~/.config/grok-cli/google_credentials.json")
                    creds = None

        if creds:
            self.google_service = build('calendar', 'v3', credentials=creds)
        else:
            self.google_service = None

    def execute_sync(
        self,
        operation: str,
        provider: str = "google",
        **kwargs
    ) -> ToolResult:
        """Execute calendar operation.

        Args:
            operation: The operation to perform (list_events, create_event, etc.)
            provider: Calendar provider ('google' or 'outlook')
            **kwargs: Additional parameters for the operation

        Returns:
            ToolResult with operation results
        """
        try:
            if provider.lower() == "google":
                if not GOOGLE_AVAILABLE:
                    return ToolResult(success=False, error="Google Calendar API not available. Install google-api-python-client and google-auth packages.")
                return self._execute_google(operation, **kwargs)
            elif provider.lower() == "outlook":
                return self._execute_outlook(operation, **kwargs)
            else:
                return ToolResult(success=False, error=f"Unsupported provider: {provider}")

        except Exception as e:
            self.logger.error(f"Calendar operation failed: {e}")
            return ToolResult(success=False, error=str(e))

    def _execute_google(self, operation: str, **kwargs) -> ToolResult:
        """Execute Google Calendar operation."""
        if not self.google_service:
            return ToolResult(success=False, error="Google Calendar not authenticated. Please set up OAuth credentials.")

        try:
            if operation == "list_events":
                return self._google_list_events(**kwargs)
            elif operation == "create_event":
                return self._google_create_event(**kwargs)
            elif operation == "get_event":
                return self._google_get_event(**kwargs)
            elif operation == "update_event":
                return self._google_update_event(**kwargs)
            elif operation == "delete_event":
                return self._google_delete_event(**kwargs)
            elif operation == "list_calendars":
                return self._google_list_calendars(**kwargs)
            elif operation == "share_calendar":
                return self._google_share_calendar(**kwargs)
            elif operation == "list_permissions":
                return self._google_list_permissions(**kwargs)
            else:
                return ToolResult(success=False, error=f"Unsupported Google Calendar operation: {operation}")

        except Exception as e:
            return ToolResult(success=False, error=f"Google Calendar error: {str(e)}")

    def _execute_outlook(self, operation: str, **kwargs) -> ToolResult:
        """Execute Outlook Calendar operation."""
        if not self.outlook_token:
            return ToolResult(success=False, error="Outlook access token not configured. Set OUTLOOK_ACCESS_TOKEN environment variable.")

        headers = {
            'Authorization': f'Bearer {self.outlook_token}',
            'Content-Type': 'application/json'
        }

        try:
            if operation == "list_events":
                return self._outlook_list_events(headers, **kwargs)
            elif operation == "create_event":
                return self._outlook_create_event(headers, **kwargs)
            elif operation == "get_event":
                return self._outlook_get_event(headers, **kwargs)
            elif operation == "update_event":
                return self._outlook_update_event(headers, **kwargs)
            elif operation == "delete_event":
                return self._outlook_delete_event(headers, **kwargs)
            elif operation == "list_calendars":
                return self._outlook_list_calendars(headers, **kwargs)
            elif operation == "share_calendar":
                return self._outlook_share_calendar(headers, **kwargs)
            elif operation == "list_permissions":
                return self._outlook_list_permissions(headers, **kwargs)
            else:
                return ToolResult(success=False, error=f"Unsupported Outlook operation: {operation}")

        except Exception as e:
            return ToolResult(success=False, error=f"Outlook Calendar error: {str(e)}")

    # Google Calendar implementations
    def _google_list_events(self, calendar_id: str = "primary", max_results: int = 10, time_min: Optional[str] = None, **kwargs) -> ToolResult:
        """List events from Google Calendar."""
        if not time_min:
            time_min = datetime.utcnow().isoformat() + 'Z'

        def _list_events():
            return self.google_service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

        try:
            events_result = self._retry_api_call(_list_events)
            events = events_result.get('items', [])
            return ToolResult(success=True, data=events, metadata={'count': len(events)})
        except HttpError as e:
            return ToolResult(success=False, error=f"Google Calendar API error: {e}")
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to list events: {e}")

    def _google_create_event(self, calendar_id: str = "primary", summary: str = "", start_time: str = "", end_time: str = "", **kwargs) -> ToolResult:
        """Create event in Google Calendar."""
        event = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': kwargs.get('timezone', 'UTC')},
            'end': {'dateTime': end_time, 'timeZone': kwargs.get('timezone', 'UTC')},
        }

        if kwargs.get('description'):
            event['description'] = kwargs['description']
        if kwargs.get('location'):
            event['location'] = kwargs['location']
        if kwargs.get('attendees'):
            event['attendees'] = [{'email': email} for email in kwargs['attendees']]

        created_event = self.google_service.events().insert(calendarId=calendar_id, body=event).execute()
        return ToolResult(success=True, data=created_event)

    def _google_get_event(self, calendar_id: str = "primary", event_id: str = "", **kwargs) -> ToolResult:
        """Get specific event from Google Calendar."""
        event = self.google_service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        return ToolResult(success=True, data=event)

    def _google_update_event(self, calendar_id: str = "primary", event_id: str = "", **kwargs) -> ToolResult:
        """Update event in Google Calendar."""
        # Get existing event first
        event = self.google_service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        # Update fields
        if 'summary' in kwargs:
            event['summary'] = kwargs['summary']
        if 'description' in kwargs:
            event['description'] = kwargs['description']
        if 'start_time' in kwargs:
            event['start']['dateTime'] = kwargs['start_time']
        if 'end_time' in kwargs:
            event['end']['dateTime'] = kwargs['end_time']
        if 'attendees' in kwargs:
            event['attendees'] = [{'email': email} for email in kwargs['attendees']]

        updated_event = self.google_service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
        return ToolResult(success=True, data=updated_event)

    def _google_delete_event(self, calendar_id: str = "primary", event_id: str = "", **kwargs) -> ToolResult:
        """Delete event from Google Calendar."""
        self.google_service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return ToolResult(success=True, data={'deleted': True})

    def _google_list_calendars(self, **kwargs) -> ToolResult:
        """List available Google Calendars."""
        calendars_result = self.google_service.calendarList().list().execute()
        calendars = calendars_result.get('items', [])
        return ToolResult(success=True, data=calendars, metadata={'count': len(calendars)})

    def _google_share_calendar(self, calendar_id: str = "primary", email: str = "", role: str = "reader", **kwargs) -> ToolResult:
        """Share Google Calendar with another user."""
        rule = {
            'scope': {
                'type': 'user',
                'value': email,
            },
            'role': role  # 'reader', 'writer', 'owner'
        }

        created_rule = self.google_service.acl().insert(calendarId=calendar_id, body=rule).execute()
        return ToolResult(success=True, data=created_rule)

    def _google_list_permissions(self, calendar_id: str = "primary", **kwargs) -> ToolResult:
        """List permissions for Google Calendar."""
        acl_result = self.google_service.acl().list(calendarId=calendar_id).execute()
        rules = acl_result.get('items', [])
        return ToolResult(success=True, data=rules, metadata={'count': len(rules)})

    # Outlook Calendar implementations
    def _outlook_list_events(self, headers: dict, calendar_id: Optional[str] = None, **kwargs) -> ToolResult:
        """List events from Outlook Calendar."""
        url = "https://graph.microsoft.com/v1.0/me/events"
        if calendar_id:
            url = f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_id}/events"

        params = {}
        if kwargs.get('top'):
            params['$top'] = kwargs['top']

        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            return ToolResult(success=True, data=data.get('value', []), metadata={'count': len(data.get('value', []))})
        else:
            return ToolResult(success=False, error=f"Outlook API error: {response.text}")

    def _outlook_create_event(self, headers: dict, subject: str = "", start_time: str = "", end_time: str = "", **kwargs) -> ToolResult:
        """Create event in Outlook Calendar."""
        event_data = {
            "subject": subject,
            "start": {
                "dateTime": start_time,
                "timeZone": kwargs.get('timezone', 'UTC')
            },
            "end": {
                "dateTime": end_time,
                "timeZone": kwargs.get('timezone', 'UTC')
            }
        }

        if kwargs.get('body'):
            event_data['body'] = {'contentType': 'text', 'content': kwargs['body']}
        if kwargs.get('location'):
            event_data['location'] = {'displayName': kwargs['location']}
        if kwargs.get('attendees'):
            event_data['attendees'] = [{'emailAddress': {'address': email}, 'type': 'required'} for email in kwargs['attendees']]

        response = requests.post("https://graph.microsoft.com/v1.0/me/events", headers=headers, json=event_data)
        if response.status_code == 201:
            return ToolResult(success=True, data=response.json())
        else:
            return ToolResult(success=False, error=f"Outlook API error: {response.text}")

    def _outlook_get_event(self, headers: dict, event_id: str = "", **kwargs) -> ToolResult:
        """Get specific event from Outlook Calendar."""
        url = f"https://graph.microsoft.com/v1.0/me/events/{event_id}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return ToolResult(success=True, data=response.json())
        else:
            return ToolResult(success=False, error=f"Outlook API error: {response.text}")

    def _outlook_update_event(self, headers: dict, event_id: str = "", **kwargs) -> ToolResult:
        """Update event in Outlook Calendar."""
        update_data = {}
        if 'subject' in kwargs:
            update_data['subject'] = kwargs['subject']
        if 'body' in kwargs:
            update_data['body'] = {'contentType': 'text', 'content': kwargs['body']}
        if 'start_time' in kwargs:
            update_data['start'] = {'dateTime': kwargs['start_time'], 'timeZone': kwargs.get('timezone', 'UTC')}
        if 'end_time' in kwargs:
            update_data['end'] = {'dateTime': kwargs['end_time'], 'timeZone': kwargs.get('timezone', 'UTC')}
        if 'attendees' in kwargs:
            update_data['attendees'] = [{'emailAddress': {'address': email}, 'type': 'required'} for email in kwargs['attendees']]

        url = f"https://graph.microsoft.com/v1.0/me/events/{event_id}"
        response = requests.patch(url, headers=headers, json=update_data)
        if response.status_code == 200:
            return ToolResult(success=True, data=response.json())
        else:
            return ToolResult(success=False, error=f"Outlook API error: {response.text}")

    def _outlook_delete_event(self, headers: dict, event_id: str = "", **kwargs) -> ToolResult:
        """Delete event from Outlook Calendar."""
        url = f"https://graph.microsoft.com/v1.0/me/events/{event_id}"
        response = requests.delete(url, headers=headers)
        if response.status_code == 204:
            return ToolResult(success=True, data={'deleted': True})
        else:
            return ToolResult(success=False, error=f"Outlook API error: {response.text}")

    def _outlook_list_calendars(self, headers: dict, **kwargs) -> ToolResult:
        """List available Outlook Calendars."""
        response = requests.get("https://graph.microsoft.com/v1.0/me/calendars", headers=headers)
        if response.status_code == 200:
            data = response.json()
            return ToolResult(success=True, data=data.get('value', []), metadata={'count': len(data.get('value', []))})
        else:
            return ToolResult(success=False, error=f"Outlook API error: {response.text}")

    def _outlook_share_calendar(self, headers: dict, calendar_id: str = "", email: str = "", role: str = "read", **kwargs) -> ToolResult:
        """Share Outlook Calendar with another user."""
        # Microsoft Graph uses permissions for calendar sharing
        permission_data = {
            "emailAddress": {
                "address": email
            },
            "isInsideOrganization": False,
            "isRemovable": True,
            "role": role  # "none", "freeBusyRead", "limitedRead", "read", "write", "delegateWithoutPrivateEventAccess", "delegateWithPrivateEventAccess", "custom"
        }

        url = f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_id}/calendarPermissions"
        response = requests.post(url, headers=headers, json=permission_data)
        if response.status_code == 201:
            return ToolResult(success=True, data=response.json())
        else:
            return ToolResult(success=False, error=f"Outlook API error: {response.text}")

    def _outlook_list_permissions(self, headers: dict, calendar_id: str = "", **kwargs) -> ToolResult:
        """List permissions for Outlook Calendar."""
        url = f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_id}/calendarPermissions"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return ToolResult(success=True, data=data.get('value', []), metadata={'count': len(data.get('value', []))})
        else:
            return ToolResult(success=False, error=f"Outlook API error: {response.text}")