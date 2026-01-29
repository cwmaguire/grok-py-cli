"""Confirmation tool for user approval workflows and safety mechanisms."""

import logging
import time
from enum import Enum
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass, field

from grok_py.tools.base import SyncTool, ToolCategory, ToolResult, register_tool


logger = logging.getLogger(__name__)


class SafetyLevel(str, Enum):
    """Safety levels for confirmation requirements."""
    STRICT = "strict"      # Always confirm all operations
    MODERATE = "moderate"  # Confirm destructive operations only
    PERMISSIVE = "permissive"  # Never confirm unless explicitly requested


class OperationType(str, Enum):
    """Types of operations that may require confirmation."""
    FILE_CREATE = "file_create"
    FILE_EDIT = "file_edit"
    FILE_DELETE = "file_delete"
    BASH_COMMAND = "bash_command"
    PACKAGE_INSTALL = "package_install"
    PACKAGE_REMOVE = "package_remove"
    SERVICE_START = "service_start"
    SERVICE_STOP = "service_stop"
    CODE_EXECUTION = "code_execution"
    WEB_SEARCH = "web_search"


@dataclass
class SessionApproval:
    """Session-based approval for operation types."""
    operation_type: str
    approved_at: float
    expires_at: Optional[float] = None
    approved_by: str = "user"


@dataclass
class ConfirmationManager:
    """Manages confirmation state and approvals."""

    safety_level: SafetyLevel = SafetyLevel.MODERATE
    session_approvals: Dict[str, SessionApproval] = field(default_factory=dict)
    session_timeout: int = 3600  # 1 hour default
    destructive_operations: Set[str] = field(default_factory=lambda: {
        OperationType.FILE_DELETE,
        OperationType.PACKAGE_REMOVE,
        OperationType.SERVICE_STOP,
    })

    def requires_confirmation(self, operation_type: str, details: Dict[str, Any]) -> bool:
        """Check if an operation requires user confirmation.

        Args:
            operation_type: Type of operation
            details: Operation details

        Returns:
            True if confirmation is required
        """
        if self.safety_level == SafetyLevel.STRICT:
            return True

        if self.safety_level == SafetyLevel.PERMISSIVE:
            return False

        # Moderate: confirm destructive operations
        return operation_type in self.destructive_operations

    def is_session_approved(self, operation_type: str) -> bool:
        """Check if operation type is approved for this session.

        Args:
            operation_type: Type of operation

        Returns:
            True if approved for session
        """
        if operation_type not in self.session_approvals:
            return False

        approval = self.session_approvals[operation_type]
        current_time = time.time()

        # Check if approval has expired
        if approval.expires_at and current_time > approval.expires_at:
            del self.session_approvals[operation_type]
            return False

        return True

    def approve_session(self, operation_type: str, approved_by: str = "user") -> None:
        """Approve all operations of a type for this session.

        Args:
            operation_type: Type of operation to approve
            approved_by: Who approved it
        """
        expires_at = time.time() + self.session_timeout if self.session_timeout > 0 else None

        self.session_approvals[operation_type] = SessionApproval(
            operation_type=operation_type,
            approved_at=time.time(),
            expires_at=expires_at,
            approved_by=approved_by
        )

        logger.info(f"Session approval granted for {operation_type} by {approved_by}")

    def reject_session(self, operation_type: str) -> None:
        """Remove session approval for an operation type.

        Args:
            operation_type: Type of operation to reject
        """
        if operation_type in self.session_approvals:
            del self.session_approvals[operation_type]
            logger.info(f"Session approval revoked for {operation_type}")

    def clear_all_approvals(self) -> None:
        """Clear all session approvals."""
        self.session_approvals.clear()
        logger.info("All session approvals cleared")

    def get_approval_status(self) -> Dict[str, Any]:
        """Get current approval status.

        Returns:
            Dictionary with approval information
        """
        current_time = time.time()
        active_approvals = {}
        expired_approvals = []

        for op_type, approval in self.session_approvals.items():
            if approval.expires_at and current_time > approval.expires_at:
                expired_approvals.append(op_type)
            else:
                active_approvals[op_type] = {
                    "approved_at": approval.approved_at,
                    "expires_at": approval.expires_at,
                    "approved_by": approval.approved_by,
                    "remaining_time": approval.expires_at - current_time if approval.expires_at else None
                }

        # Clean up expired approvals
        for op_type in expired_approvals:
            del self.session_approvals[op_type]

        return {
            "safety_level": self.safety_level.value,
            "session_timeout": self.session_timeout,
            "active_approvals": active_approvals,
            "expired_approvals": expired_approvals,
            "destructive_operations": list(self.destructive_operations)
        }


@register_tool(
    category=ToolCategory.UTILITY,
    name="confirmation",
    description="User confirmation system for operations with configurable safety levels and session approvals"
)
class ConfirmationTool(SyncTool):
    """Tool for managing user confirmations and safety settings."""

    def __init__(self):
        super().__init__(
            name="confirmation",
            description="User confirmation system for operations with configurable safety levels and session approvals",
            category=ToolCategory.UTILITY
        )
        self.manager = ConfirmationManager()

    def execute_sync(
        self,
        action: str,
        operation_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        safety_level: Optional[str] = None,
        session_timeout: Optional[int] = None
    ) -> ToolResult:
        """Execute confirmation-related actions.

        Args:
            action: Action to perform ('check', 'approve_session', 'reject_session', 'clear_all', 'get_status', 'set_safety', 'set_timeout')
            operation_type: Type of operation for approval actions
            details: Operation details for confirmation check
            safety_level: Safety level to set ('strict', 'moderate', 'permissive')
            session_timeout: Session timeout in seconds

        Returns:
            ToolResult: Result of the confirmation action
        """
        try:
            if action == "check":
                return self._check_confirmation(operation_type, details or {})
            elif action == "approve_session":
                return self._approve_session(operation_type)
            elif action == "reject_session":
                return self._reject_session(operation_type)
            elif action == "clear_all":
                return self._clear_all_approvals()
            elif action == "get_status":
                return self._get_status()
            elif action == "set_safety":
                return self._set_safety_level(safety_level)
            elif action == "set_timeout":
                return self._set_session_timeout(session_timeout)
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown action: {action}",
                    data={"available_actions": ["check", "approve_session", "reject_session", "clear_all", "get_status", "set_safety", "set_timeout"]}
                )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Confirmation action failed: {str(e)}"
            )

    def _check_confirmation(self, operation_type: Optional[str], details: Dict[str, Any]) -> ToolResult:
        """Check if confirmation is required for an operation."""
        if not operation_type:
            return ToolResult(
                success=False,
                error="operation_type is required for check action"
            )

        requires_confirmation = self.manager.requires_confirmation(operation_type, details)
        session_approved = self.manager.is_session_approved(operation_type)

        return ToolResult(
            success=True,
            data={
                "operation_type": operation_type,
                "requires_confirmation": requires_confirmation,
                "session_approved": session_approved,
                "can_proceed": not requires_confirmation or session_approved,
                "safety_level": self.manager.safety_level.value
            }
        )

    def _approve_session(self, operation_type: Optional[str]) -> ToolResult:
        """Approve all operations of a type for this session."""
        if not operation_type:
            return ToolResult(
                success=False,
                error="operation_type is required for approve_session action"
            )

        self.manager.approve_session(operation_type)

        return ToolResult(
            success=True,
            data={
                "operation_type": operation_type,
                "action": "approved",
                "session_timeout": self.manager.session_timeout
            }
        )

    def _reject_session(self, operation_type: Optional[str]) -> ToolResult:
        """Reject session approval for an operation type."""
        if not operation_type:
            return ToolResult(
                success=False,
                error="operation_type is required for reject_session action"
            )

        self.manager.reject_session(operation_type)

        return ToolResult(
            success=True,
            data={
                "operation_type": operation_type,
                "action": "rejected"
            }
        )

    def _clear_all_approvals(self) -> ToolResult:
        """Clear all session approvals."""
        self.manager.clear_all_approvals()

        return ToolResult(
            success=True,
            data={"action": "cleared_all_approvals"}
        )

    def _get_status(self) -> ToolResult:
        """Get current confirmation status."""
        status = self.manager.get_approval_status()

        return ToolResult(
            success=True,
            data=status
        )

    def _set_safety_level(self, safety_level: Optional[str]) -> ToolResult:
        """Set the safety level."""
        if not safety_level:
            return ToolResult(
                success=False,
                error="safety_level is required for set_safety action"
            )

        try:
            level = SafetyLevel(safety_level.lower())
            self.manager.safety_level = level

            return ToolResult(
                success=True,
                data={
                    "action": "set_safety_level",
                    "safety_level": level.value
                }
            )
        except ValueError:
            return ToolResult(
                success=False,
                error=f"Invalid safety level: {safety_level}. Must be one of: {[l.value for l in SafetyLevel]}"
            )

    def _set_session_timeout(self, timeout: Optional[int]) -> ToolResult:
        """Set the session timeout."""
        if timeout is None:
            return ToolResult(
                success=False,
                error="session_timeout is required for set_timeout action"
            )

        if timeout < 0:
            return ToolResult(
                success=False,
                error="session_timeout must be non-negative"
            )

        self.manager.session_timeout = timeout

        return ToolResult(
            success=True,
            data={
                "action": "set_session_timeout",
                "session_timeout": timeout
            }
        )