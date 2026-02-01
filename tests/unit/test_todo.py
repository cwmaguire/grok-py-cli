"""Unit tests for TodoTool."""

import pytest
from unittest.mock import patch
from grok_py.tools.todo import TodoTool, TodoItem
from grok_py.tools.base import ToolResult


class TestTodoItem:
    """Test TodoItem class."""

    def test_init(self):
        """Test TodoItem initialization."""
        item = TodoItem(id="test-1", content="Test todo", status="pending", priority="high")
        assert item.id == "test-1"
        assert item.content == "Test todo"
        assert item.status == "pending"
        assert item.priority == "high"
        assert item.created_at is not None
        assert item.updated_at is not None

    def test_to_dict(self):
        """Test TodoItem to_dict conversion."""
        item = TodoItem(id="test-1", content="Test todo", status="completed", priority="low")
        data = item.to_dict()
        assert data['id'] == "test-1"
        assert data['content'] == "Test todo"
        assert data['status'] == "completed"
        assert data['priority'] == "low"
        assert 'created_at' in data
        assert 'updated_at' in data

    def test_from_dict(self):
        """Test TodoItem from_dict creation."""
        data = {
            'id': 'test-1',
            'content': 'Test content',
            'status': 'in_progress',
            'priority': 'medium',
            'created_at': '2023-01-01T12:00:00',
            'updated_at': '2023-01-02T12:00:00'
        }
        item = TodoItem.from_dict(data)
        assert item.id == 'test-1'
        assert item.content == 'Test content'
        assert item.status == 'in_progress'
        assert item.priority == 'medium'

    def test_from_dict_defaults(self):
        """Test TodoItem from_dict with missing optional fields."""
        data = {'id': 'test-1', 'content': 'Test'}
        item = TodoItem.from_dict(data)
        assert item.status == 'pending'
        assert item.priority == 'medium'


class TestTodoTool:
    """Test TodoTool class."""

    def setup_method(self):
        """Set up test method."""
        self.tool = TodoTool()

    def test_init(self):
        """Test TodoTool initialization."""
        assert self.tool.name == "todo"
        assert self.tool.description == "Task planning and tracking with visual progress indicators"
        assert self.tool.todos == {}

    def test_execute_sync_create_valid(self):
        """Test execute_sync with valid create_todo_list operation."""
        todos = [
            {'id': '1', 'content': 'First task', 'status': 'pending', 'priority': 'high'},
            {'content': 'Second task', 'status': 'in_progress', 'priority': 'medium'}
        ]
        result = self.tool.execute_sync(operation='create_todo_list', todos=todos)
        assert result.success is True
        assert result.data['operation'] == 'create_todo_list'
        assert len(result.data['created_todos']) == 2
        assert '1' in self.tool.todos
        assert result.data['total_created'] == 2

    def test_execute_sync_create_empty(self):
        """Test execute_sync with empty todos list."""
        result = self.tool.execute_sync(operation='create_todo_list', todos=[])
        assert result.success is False
        assert "No todos provided" in result.error

    def test_execute_sync_create_invalid_data(self):
        """Test execute_sync with invalid todo data."""
        todos = [{'invalid': 'data'}]  # Missing content
        result = self.tool.execute_sync(operation='create_todo_list', todos=todos)
        assert result.success is False
        assert "must have 'content' field" in result.error

    def test_execute_sync_create_invalid_status(self):
        """Test execute_sync with invalid status."""
        todos = [{'content': 'Test', 'status': 'invalid'}]
        result = self.tool.execute_sync(operation='create_todo_list', todos=todos)
        assert result.success is False
        assert "Invalid status 'invalid'" in result.error

    def test_execute_sync_create_duplicate_id(self):
        """Test execute_sync with duplicate ID."""
        todos = [{'id': 'dup', 'content': 'First'}, {'id': 'dup', 'content': 'Second'}]
        result = self.tool.execute_sync(operation='create_todo_list', todos=todos)
        assert result.success is False
        assert "already exists" in result.error

    def test_execute_sync_update_valid(self):
        """Test execute_sync with valid update_todo_list operation."""
        # First create a todo
        self.tool.execute_sync(operation='create_todo_list', todos=[{'id': '1', 'content': 'Test'}])
        updates = [{'id': '1', 'status': 'completed', 'priority': 'low'}]
        result = self.tool.execute_sync(operation='update_todo_list', updates=updates)
        assert result.success is True
        assert result.data['operation'] == 'update_todo_list'
        assert len(result.data['updated_todos']) == 1
        assert self.tool.todos['1'].status == 'completed'
        assert self.tool.todos['1'].priority == 'low'

    def test_execute_sync_update_empty(self):
        """Test execute_sync with empty updates."""
        result = self.tool.execute_sync(operation='update_todo_list', updates=[])
        assert result.success is False
        assert "No updates provided" in result.error

    def test_execute_sync_update_not_found(self):
        """Test execute_sync with non-existent todo ID."""
        updates = [{'id': 'nonexistent', 'status': 'completed'}]
        result = self.tool.execute_sync(operation='update_todo_list', updates=updates)
        assert result.success is False
        assert "not found" in result.error

    def test_execute_sync_update_invalid_status(self):
        """Test execute_sync with invalid status in update."""
        self.tool.execute_sync(operation='create_todo_list', todos=[{'id': '1', 'content': 'Test'}])
        updates = [{'id': '1', 'status': 'invalid'}]
        result = self.tool.execute_sync(operation='update_todo_list', updates=updates)
        assert result.success is False
        assert "Invalid status 'invalid'" in result.error

    def test_execute_sync_invalid_operation(self):
        """Test execute_sync with invalid operation."""
        result = self.tool.execute_sync(operation='invalid')
        assert result.success is False
        assert "Invalid operation" in result.error

    def test_generate_visual_list_empty(self):
        """Test _generate_visual_list with no todos."""
        result = self.tool._generate_visual_list([])
        assert "No todos found" in result

    def test_generate_visual_list_with_todos(self):
        """Test _generate_visual_list with todos."""
        todos = [
            {'content': 'Pending high', 'status': 'pending', 'priority': 'high'},
            {'content': 'In progress medium', 'status': 'in_progress', 'priority': 'medium'},
            {'content': 'Completed low', 'status': 'completed', 'priority': 'low'}
        ]
        result = self.tool._generate_visual_list(todos)
        assert "📋 Todo List" in result
        assert "⏳ Pending" in result
        assert "🔄 In Progress" in result
        assert "✅ Completed" in result
        assert "Summary:" in result

    def test_get_all_todos(self):
        """Test get_all_todos method."""
        self.tool.execute_sync(operation='create_todo_list', todos=[{'id': '1', 'content': 'Test'}])
        todos = self.tool.get_all_todos()
        assert len(todos) == 1
        assert todos[0]['id'] == '1'

    def test_get_todo_by_id(self):
        """Test get_todo_by_id method."""
        self.tool.execute_sync(operation='create_todo_list', todos=[{'id': '1', 'content': 'Test'}])
        todo = self.tool.get_todo_by_id('1')
        assert todo is not None
        assert todo['content'] == 'Test'
        assert self.tool.get_todo_by_id('nonexistent') is None

    def test_clear_all_todos(self):
        """Test clear_all_todos method."""
        self.tool.execute_sync(operation='create_todo_list', todos=[{'id': '1', 'content': 'Test'}])
        count = self.tool.clear_all_todos()
        assert count == 1
        assert len(self.tool.todos) == 0