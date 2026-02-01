"""Unit tests for ConfirmationTool."""

import time
import pytest
from unittest.mock import patch
from grok_py.tools.confirmation import (
    ConfirmationTool,
    ConfirmationManager,
    SafetyLevel,
    OperationType,
    SessionApproval
)
from grok_py.tools.base import ToolResult


class TestSafetyLevel:
    """Test SafetyLevel enum."""

    def test_enum_values(self):
        """Test SafetyLevel enum values."""
        assert SafetyLevel.STRICT == "strict"
        assert SafetyLevel.MODERATE == "moderate"
        assert SafetyLevel.PERMISSIVE == "permissive"


class TestOperationType:
    """Test OperationType enum."""

    def test_enum_values(self):
        """Test OperationType enum values."""
        assert OperationType.FILE_CREATE == "file_create"
        assert OperationType.FILE_EDIT == "file_edit"
        assert OperationType.FILE_DELETE == "file_delete"
        assert OperationType.BASH_COMMAND == "bash_command"
        assert OperationType.PACKAGE_INSTALL == "package_install"
        assert OperationType.PACKAGE_REMOVE == "package_remove"
        assert OperationType.SERVICE_START == "service_start"
        assert OperationType.SERVICE_STOP == "service_stop"
        assert OperationType.CODE_EXECUTION == "code_execution"
        assert OperationType.WEB_SEARCH == "web_search"


class TestSessionApproval:
    """Test SessionApproval dataclass."""

    def test_init(self):
        """Test SessionApproval initialization."""
        approval = SessionApproval(
            operation_type="file_delete",
            approved_at=1234567890.0,
            expires_at=1234567900.0,
            approved_by="user"
        )
        assert approval.operation_type == "file_delete"
        assert approval.approved_at == 1234567890.0
        assert approval.expires_at == 1234567900.0
        assert approval.approved_by == "user"


class TestConfirmationManager:
    """Test ConfirmationManager class."""

    def setup_method(self):
        """Set up test method."""
        self.manager = ConfirmationManager()

    def test_init(self):
        """Test ConfirmationManager initialization."""
        assert self.manager.safety_level == SafetyLevel.MODERATE
        assert self.manager.session_approvals == {}
        assert self.manager.session_timeout == 3600
        assert OperationType.FILE_DELETE in self.manager.destructive_operations
        assert OperationType.PACKAGE_REMOVE in self.manager.destructive_operations
        assert OperationType.SERVICE_STOP in self.manager.destructive_operations

    def test_requires_confirmation_strict(self):
        """Test requires_confirmation with STRICT safety level."""
        self.manager.safety_level = SafetyLevel.STRICT
        assert self.manager.requires_confirmation("file_create", {}) is True
        assert self.manager.requires_confirmation("file_delete", {}) is True

    def test_requires_confirmation_permissive(self):
        """Test requires_confirmation with PERMISSIVE safety level."""
        self.manager.safety_level = SafetyLevel.PERMISSIVE
        assert self.manager.requires_confirmation("file_delete", {}) is False

    def test_requires_confirmation_moderate_destructive(self):
        """Test requires_confirmation with MODERATE safety level for destructive operations."""
        self.manager.safety_level = SafetyLevel.MODERATE
        assert self.manager.requires_confirmation("file_delete", {}) is True
        assert self.manager.requires_confirmation("file_create", {}) is False

    def test_is_session_approved_not_approved(self):
        """Test is_session_approved when not approved."""
        assert self.manager.is_session_approved("file_delete") is False

    def test_is_session_approved_expired(self):
        """Test is_session_approved when approval is expired."""
        past_time = time.time() - 100
        self.manager.session_approvals["file_delete"] = SessionApproval(
            operation_type="file_delete",
            approved_at=past_time,
            expires_at=past_time + 50  # Expired
        )
        assert self.manager.is_session_approved("file_delete") is False
        assert "file_delete" not in self.manager.session_approvals

    def test_is_session_approved_valid(self):
        """Test is_session_approved when approval is valid."""
        future_time = time.time() + 100
        self.manager.session_approvals["file_delete"] = SessionApproval(
            operation_type="file_delete",
            approved_at=time.time(),
            expires_at=future_time
        )
        assert self.manager.is_session_approved("file_delete") is True

    def test_approve_session(self):
        """Test approve_session method."""
        self.manager.approve_session("file_delete", "test_user")
        assert "file_delete" in self.manager.session_approvals
        approval = self.manager.session_approvals["file_delete"]
        assert approval.operation_type == "file_delete"
        assert approval.approved_by == "test_user"
        assert approval.expires_at is not None

    def test_approve_session_no_timeout(self):
        """Test approve_session with no timeout."""
        self.manager.session_timeout = 0
        self.manager.approve_session("file_delete")
        approval = self.manager.session_approvals["file_delete"]
        assert approval.expires_at is None

    def test_reject_session(self):
        """Test reject_session method."""
        self.manager.session_approvals["file_delete"] = SessionApproval(
            operation_type="file_delete",
            approved_at=time.time()
        )
        self.manager.reject_session("file_delete")
        assert "file_delete" not in self.manager.session_approvals

    def test_clear_all_approvals(self):
        """Test clear_all_approvals method."""
        self.manager.session_approvals["file_delete"] = SessionApproval(
            operation_type="file_delete",
            approved_at=time.time()
        )
        self.manager.session_approvals["file_create"] = SessionApproval(
            operation_type="file_create",
            approved_at=time.time()
        )
        self.manager.clear_all_approvals()
        assert self.manager.session_approvals == {}

    def test_get_approval_status(self):
        """Test get_approval_status method."""
        future_time = time.time() + 100
        self.manager.session_approvals["file_delete"] = SessionApproval(
            operation_type="file_delete",
            approved_at=time.time(),
            expires_at=future_time,
            approved_by="user"
        )
        status = self.manager.get_approval_status()
        assert status["safety_level"] == "moderate"
        assert status["session_timeout"] == 3600
        assert "file_delete" in status["active_approvals"]
        assert status["expired_approvals"] == []
        assert OperationType.FILE_DELETE in status["destructive_operations"]


class TestConfirmationTool:
    """Test ConfirmationTool class."""

    def setup_method(self):
        """Set up test method."""
        self.tool = ConfirmationTool()

    def test_init(self):
        """Test ConfirmationTool initialization."""
        assert self.tool.name == "confirmation"
        assert self.tool.description == "User confirmation system for operations with configurable safety levels and session approvals"
        assert isinstance(self.tool.manager, ConfirmationManager)

    def test_execute_sync_check_valid(self):
        """Test execute_sync with check action."""
        result = self.tool.execute_sync(action="check", operation_type="file_delete", details={})
        assert result.success is True
        assert result.data["operation_type"] == "file_delete"
        assert result.data["requires_confirmation"] is True  # Moderate level, destructive
        assert result.data["session_approved"] is False
        assert result.data["can_proceed"] is False

    def test_execute_sync_check_no_operation_type(self):
        """Test execute_sync check without operation_type."""
        result = self.tool.execute_sync(action="check")
        assert result.success is False
        assert "operation_type is required" in result.error

    def test_execute_sync_approve_session_valid(self):
        """Test execute_sync with approve_session action."""
        result = self.tool.execute_sync(action="approve_session", operation_type="file_delete")
        assert result.success is True
        assert result.data["operation_type"] == "file_delete"
        assert result.data["action"] == "approved"
        assert "file_delete" in self.tool.manager.session_approvals

    def test_execute_sync_approve_session_no_operation_type(self):
        """Test execute_sync approve_session without operation_type."""
        result = self.tool.execute_sync(action="approve_session")
        assert result.success is False
        assert "operation_type is required" in result.error

    def test_execute_sync_reject_session_valid(self):
        """Test execute_sync with reject_session action."""
        self.tool.manager.session_approvals["file_delete"] = SessionApproval(
            operation_type="file_delete",
            approved_at=time.time()
        )
        result = self.tool.execute_sync(action="reject_session", operation_type="file_delete")
        assert result.success is True
        assert result.data["action"] == "rejected"
        assert "file_delete" not in self.tool.manager.session_approvals

    def test_execute_sync_clear_all(self):
        """Test execute_sync with clear_all action."""
        self.tool.manager.session_approvals["file_delete"] = SessionApproval(
            operation_type="file_delete",
            approved_at=time.time()
        )
        result = self.tool.execute_sync(action="clear_all")
        assert result.success is True
        assert result.data["action"] == "cleared_all_approvals"
        assert self.tool.manager.session_approvals == {}

    def test_execute_sync_get_status(self):
        """Test execute_sync with get_status action."""
        result = self.tool.execute_sync(action="get_status")
        assert result.success is True
        assert "safety_level" in result.data
        assert "active_approvals" in result.data

    def test_execute_sync_set_safety_valid(self):
        """Test execute_sync with set_safety action."""
        result = self.tool.execute_sync(action="set_safety", safety_level="strict")
        assert result.success is True
        assert result.data["safety_level"] == "strict"
        assert self.tool.manager.safety_level == SafetyLevel.STRICT

    def test_execute_sync_set_safety_invalid(self):
        """Test execute_sync set_safety with invalid level."""
        result = self.tool.execute_sync(action="set_safety", safety_level="invalid")
        assert result.success is False
        assert "Invalid safety level" in result.error

    def test_execute_sync_set_safety_no_level(self):
        """Test execute_sync set_safety without safety_level."""
        result = self.tool.execute_sync(action="set_safety")
        assert result.success is False
        assert "safety_level is required" in result.error

    def test_execute_sync_set_timeout_valid(self):
        """Test execute_sync with set_timeout action."""
        result = self.tool.execute_sync(action="set_timeout", session_timeout=7200)
        assert result.success is True
        assert self.tool.manager.session_timeout == 7200

    def test_execute_sync_set_timeout_negative(self):
        """Test execute_sync set_timeout with negative value."""
        result = self.tool.execute_sync(action="set_timeout", session_timeout=-1)
        assert result.success is False
        assert "must be non-negative" in result.error

    def test_execute_sync_set_timeout_no_timeout(self):
        """Test execute_sync set_timeout without session_timeout."""
        result = self.tool.execute_sync(action="set_timeout")
        assert result.success is False
        assert "session_timeout is required" in result.error

    def test_execute_sync_unknown_action(self):
        """Test execute_sync with unknown action."""
        result = self.tool.execute_sync(action="unknown")
        assert result.success is False
        assert "Unknown action" in result.error
        assert "available_actions" in result.data