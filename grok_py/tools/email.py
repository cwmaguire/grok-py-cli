"""Email tool for SMTP/IMAP integration, sending and receiving emails with secure authentication."""

import os
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, Dict, Any, List
from datetime import datetime
import ssl
import base64

from .base import SyncTool, ToolCategory, ToolResult


class EmailTool(SyncTool):
    name = "email"
    description = "Email operations including sending, receiving, and managing emails via SMTP/IMAP"
    category = ToolCategory.WEB

    def __init__(self):
        super().__init__()
        self.smtp_server = None
        self.imap_server = None
        self.email = None
        self.password = None
        self.access_token = None
        self.use_oauth = False
        self._initialize_connection()

    def _initialize_connection(self):
        """Initialize email connection parameters from environment variables."""
        self.email = os.getenv("EMAIL_USER")
        self.password = os.getenv("EMAIL_PASSWORD")
        self.access_token = os.getenv("EMAIL_ACCESS_TOKEN")
        self.use_oauth = bool(self.access_token)
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")
        self.imap_port = int(os.getenv("IMAP_PORT", "993"))

    def _get_oauth_auth_string(self) -> str:
        """Generate OAuth authentication string for XOAUTH2."""
        if not self.email or not self.access_token:
            raise ValueError("Email and access token required for OAuth")
        auth_string = f"user={self.email}\x01auth=Bearer {self.access_token}\x01\x01"
        return base64.b64encode(auth_string.encode()).decode()

    def execute_sync(self, operation: str, **kwargs) -> ToolResult:
        """Execute email operations synchronously."""
        if operation == "send_email":
            return self.send_email(**kwargs)
        elif operation == "receive_emails":
            return self.receive_emails(**kwargs)
        elif operation == "search_emails":
            return self.search_emails(**kwargs)
        else:
            return ToolResult(success=False, error=f"Unknown operation: {operation}")

    def send_email(self, to: str, subject: str, body: str, attachments: Optional[List[str]] = None) -> ToolResult:
        """Send an email with optional attachments."""
        try:
            if not self.email:
                return ToolResult(success=False, error="Email address not configured")
            if not self.use_oauth and not self.password:
                return ToolResult(success=False, error="Email credentials not configured")

            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = to
            msg['Subject'] = subject

            # Add body
            msg.attach(MIMEText(body, 'plain'))

            # Add attachments
            if attachments:
                for file_path in attachments:
                    if os.path.isfile(file_path):
                        with open(file_path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(file_path)}')
                            msg.attach(part)

            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                if self.use_oauth:
                    auth_string = self._get_oauth_auth_string()
                    server.docmd("AUTH", f"XOAUTH2 {auth_string}")
                else:
                    server.login(self.email, self.password)
                server.sendmail(self.email, to, msg.as_string())

            return ToolResult(success=True, data={"message": "Email sent successfully"})
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to send email: {str(e)}")

    def receive_emails(self, mailbox: str = "INBOX", limit: int = 10) -> ToolResult:
        """Receive and parse emails from mailbox."""
        try:
            if not self.email:
                return ToolResult(success=False, error="Email address not configured")
            if not self.use_oauth and not self.password:
                return ToolResult(success=False, error="Email credentials not configured")

            # Connect to IMAP
            mail = imaplib.IMAP4_SSL(self.imap_server)
            if self.use_oauth:
                auth_string = self._get_oauth_auth_string()
                mail.authenticate("XOAUTH2", lambda x: auth_string)
            else:
                mail.login(self.email, self.password)
            mail.select(mailbox)

            # Get emails
            status, messages = mail.search(None, 'ALL')
            email_ids = messages[0].split()[-limit:]  # Get last 'limit' emails

            emails = []
            for email_id in email_ids:
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                raw_email = msg_data[0][1]
                email_message = email.message_from_bytes(raw_email)

                email_data = {
                    "id": email_id.decode(),
                    "from": email_message.get("From"),
                    "to": email_message.get("To"),
                    "subject": email_message.get("Subject"),
                    "date": email_message.get("Date"),
                    "body": self._get_email_body(email_message)
                }
                emails.append(email_data)

            mail.logout()
            return ToolResult(success=True, data={"emails": emails})
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to receive emails: {str(e)}")

    def search_emails(self, query: str, mailbox: str = "INBOX", limit: int = 10) -> ToolResult:
        """Search emails based on query."""
        try:
            if not self.email:
                return ToolResult(success=False, error="Email address not configured")
            if not self.use_oauth and not self.password:
                return ToolResult(success=False, error="Email credentials not configured")

            # Connect to IMAP
            mail = imaplib.IMAP4_SSL(self.imap_server)
            if self.use_oauth:
                auth_string = self._get_oauth_auth_string()
                mail.authenticate("XOAUTH2", lambda x: auth_string)
            else:
                mail.login(self.email, self.password)
            mail.select(mailbox)

            # Search emails
            status, messages = mail.search(None, query)
            email_ids = messages[0].split()[-limit:]  # Get last 'limit' matching emails

            emails = []
            for email_id in email_ids:
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                raw_email = msg_data[0][1]
                email_message = email.message_from_bytes(raw_email)

                email_data = {
                    "id": email_id.decode(),
                    "from": email_message.get("From"),
                    "to": email_message.get("To"),
                    "subject": email_message.get("Subject"),
                    "date": email_message.get("Date"),
                    "body": self._get_email_body(email_message)
                }
                emails.append(email_data)

            mail.logout()
            return ToolResult(success=True, data={"emails": emails})
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to search emails: {str(e)}")

    def _get_email_body(self, email_message) -> str:
        """Extract plain text body from email message."""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            return email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
        return ""