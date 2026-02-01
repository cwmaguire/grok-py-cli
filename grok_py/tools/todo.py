"""Todo list management tool for task planning and tracking."""

import uuid
from datetime import datetime
from typing import List, Optional

from .base import SyncTool, ToolCategory, ToolResult


class TodoItem:
    """Represents a single todo item."""

    def __init__(self, id: str, content: str, status: str = "pending", priority: str = "medium"):
        self.id = id
        self.content = content
        self.status = status  # pending, in_progress, completed
        self.priority = priority  # high, medium, low
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """Convert todo item to dictionary."""
        return {
            'id': self.id,
            'content': self.content,
            'status': self.status,
            'priority': self.priority,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TodoItem':
        """Create todo item from dictionary."""
        item = cls(
            id=data['id'],
            content=data['content'],
            status=data.get('status', 'pending'),
            priority=data.get('priority', 'medium')
        )
        if 'created_at' in data:
            item.created_at = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data:
            item.updated_at = datetime.fromisoformat(data['updated_at'])
        return item


class TodoTool(SyncTool):
    """Tool for managing todo lists and task tracking."""

    def __init__(self):
        super().__init__(
            name="todo",
            description="Task planning and tracking with visual progress indicators",
            category=ToolCategory.UTILITY
        )

        # In-memory storage for todo items
        # In a production system, this would be persisted to disk/database
        self.todos = {}

    def execute_sync(
        self,
        operation: str,
        todos: Optional[List[dict]] = None,
        updates: Optional[List[dict]] = None
    ) -> ToolResult:
        """Execute todo management operation.

        Args:
            operation: Operation to perform ('create_todo_list' or 'update_todo_list')
            todos: List of todo items for creation (required for create_todo_list)
            updates: List of todo updates (required for update_todo_list)

        Returns:
            ToolResult with operation result
        """
        try:
            if operation == 'create_todo_list':
                return self._create_todo_list(todos or [])
            elif operation == 'update_todo_list':
                return self._update_todo_list(updates or [])
            else:
                return ToolResult(
                    success=False,
                    error=f"Invalid operation: {operation}. Valid operations: create_todo_list, update_todo_list"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Todo operation failed: {str(e)}"
            )

    def _create_todo_list(self, todos_data: List[dict]) -> ToolResult:
        """Create a new todo list."""
        try:
            if not todos_data:
                return ToolResult(
                    success=False,
                    error="No todos provided for creation"
                )

            # Validate todo data
            created_todos = []
            for todo_data in todos_data:
                if not isinstance(todo_data, dict):
                    return ToolResult(
                        success=False,
                        error="Each todo must be a dictionary"
                    )

                # Validate required fields
                if 'content' not in todo_data:
                    return ToolResult(
                        success=False,
                        error="Each todo must have 'content' field"
                    )

                # Generate unique ID
                todo_id = todo_data.get('id', str(uuid.uuid4()))

                # Validate status and priority
                status = todo_data.get('status', 'pending')
                priority = todo_data.get('priority', 'medium')

                if status not in ['pending', 'in_progress', 'completed']:
                    return ToolResult(
                        success=False,
                        error=f"Invalid status '{status}'. Must be: pending, in_progress, completed"
                    )

                if priority not in ['high', 'medium', 'low']:
                    return ToolResult(
                        success=False,
                        error=f"Invalid priority '{priority}'. Must be: high, medium, low"
                    )

                # Check for duplicate ID
                if todo_id in self.todos:
                    return ToolResult(
                        success=False,
                        error=f"Todo with ID '{todo_id}' already exists"
                    )

                # Create todo item
                todo_item = TodoItem(
                    id=todo_id,
                    content=todo_data['content'],
                    status=status,
                    priority=priority
                )

                self.todos[todo_id] = todo_item
                created_todos.append(todo_item.to_dict())

            # Generate visual representation
            visual_list = self._generate_visual_list(created_todos)

            result_data = {
                'operation': 'create_todo_list',
                'created_todos': created_todos,
                'total_created': len(created_todos),
                'visual_list': visual_list
            }

            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    'total_todos': len(self.todos),
                    'created_count': len(created_todos),
                    'operation': 'create'
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to create todo list: {str(e)}"
            )

    def _update_todo_list(self, updates: List[dict]) -> ToolResult:
        """Update existing todos."""
        try:
            if not updates:
                return ToolResult(
                    success=False,
                    error="No updates provided"
                )

            updated_todos = []
            not_found_ids = []

            for update in updates:
                if not isinstance(update, dict):
                    return ToolResult(
                        success=False,
                        error="Each update must be a dictionary"
                    )

                todo_id = update.get('id')
                if not todo_id:
                    return ToolResult(
                        success=False,
                        error="Each update must have 'id' field"
                    )

                if todo_id not in self.todos:
                    not_found_ids.append(todo_id)
                    continue

                todo_item = self.todos[todo_id]

                # Update fields
                if 'content' in update:
                    todo_item.content = update['content']

                if 'status' in update:
                    new_status = update['status']
                    if new_status not in ['pending', 'in_progress', 'completed']:
                        return ToolResult(
                            success=False,
                            error=f"Invalid status '{new_status}'. Must be: pending, in_progress, completed"
                        )
                    todo_item.status = new_status

                if 'priority' in update:
                    new_priority = update['priority']
                    if new_priority not in ['high', 'medium', 'low']:
                        return ToolResult(
                            success=False,
                            error=f"Invalid priority '{new_priority}'. Must be: high, medium, low"
                        )
                    todo_item.priority = new_priority

                # Update timestamp
                todo_item.updated_at = datetime.now()
                updated_todos.append(todo_item.to_dict())

            if not_found_ids:
                return ToolResult(
                    success=False,
                    error=f"Todo IDs not found: {', '.join(not_found_ids)}"
                )

            # Generate visual representation of all todos
            all_todos = [todo.to_dict() for todo in self.todos.values()]
            visual_list = self._generate_visual_list(all_todos)

            result_data = {
                'operation': 'update_todo_list',
                'updated_todos': updated_todos,
                'total_updated': len(updated_todos),
                'visual_list': visual_list
            }

            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    'total_todos': len(self.todos),
                    'updated_count': len(updated_todos),
                    'operation': 'update'
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to update todos: {str(e)}"
            )

    def _generate_visual_list(self, todos: List[dict]) -> str:
        """Generate a visual representation of the todo list with colors."""
        if not todos:
            return "No todos found."

        lines = []
        lines.append("📋 Todo List\n")

        # Group by status
        status_groups = {
            'pending': [],
            'in_progress': [],
            'completed': []
        }

        for todo in todos:
            status_groups[todo['status']].append(todo)

        # Status indicators with colors
        status_indicators = {
            'pending': '⏳',      # Yellow/cyan
            'in_progress': '🔄',  # Cyan
            'completed': '✅'     # Green
        }

        # Priority indicators
        priority_indicators = {
            'high': '🔴',    # Red
            'medium': '🟡',  # Yellow
            'low': '🟢'      # Green
        }

        # Display each status group
        for status in ['in_progress', 'pending', 'completed']:
            group_todos = status_groups[status]
            if group_todos:
                status_icon = status_indicators[status]
                status_label = status.replace('_', ' ').title()
                lines.append(f"{status_icon} {status_label} ({len(group_todos)})")
                lines.append("─" * 40)

                for todo in group_todos:
                    priority_icon = priority_indicators[todo['priority']]
                    content = todo['content'][:60] + "..." if len(todo['content']) > 60 else todo['content']
                    line = f"  {priority_icon} {content}"
                    lines.append(line)

                lines.append("")  # Empty line between groups

        # Summary
        total = len(todos)
        completed = len(status_groups['completed'])
        in_progress = len(status_groups['in_progress'])
        pending = len(status_groups['pending'])

        summary = f"📊 Summary: {completed}/{total} completed"
        if in_progress > 0:
            summary += f", {in_progress} in progress"
        if pending > 0:
            summary += f", {pending} pending"

        lines.append(summary)

        return "\n".join(lines)

    def get_all_todos(self) -> List[dict]:
        """Get all todos as dictionaries."""
        return [todo.to_dict() for todo in self.todos.values()]

    def get_todo_by_id(self, todo_id: str) -> Optional[dict]:
        """Get a specific todo by ID."""
        todo = self.todos.get(todo_id)
        return todo.to_dict() if todo else None

    def clear_all_todos(self) -> int:
        """Clear all todos. Returns the number of todos cleared."""
        count = len(self.todos)
        self.todos.clear()
        return count