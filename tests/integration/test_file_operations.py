"""Integration tests for file operations workflow."""

import pytest
from pathlib import Path

from grok_py.tools.file_tools import CreateFileTool, ViewFileTool, SearchTool, StrReplaceEditorTool


class TestFileOperationsIntegration:
    """Integration tests for file operations workflow."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create a temporary directory for testing."""
        return tmp_path

    def test_file_workflow_create_view(self, temp_dir):
        """Test creating a file and viewing it."""
        create_tool = CreateFileTool()
        view_tool = ViewFileTool()

        file_path = temp_dir / "test.txt"
        content = "Hello, World!\nThis is a test file.\nWith multiple lines."

        # Create file
        create_result = create_tool.execute_sync(path=str(file_path), content=content)
        assert create_result.success is True
        assert create_result.data['path'] == str(file_path)
        assert create_result.data['content_length'] == len(content)

        # View file
        view_result = view_tool.execute_sync(path=str(file_path))
        assert view_result.success is True
        assert view_result.data['type'] == "file"
        assert view_result.data['content'] == content
        assert view_result.data['total_lines'] == 3

        # View partial
        partial_result = view_tool.execute_sync(path=str(file_path), start_line=2, end_line=3)
        assert partial_result.success is True
        assert partial_result.data['content'] == "This is a test file.\nWith multiple lines."
        assert partial_result.data['line_info'] == "Lines 2-3 of 3"

    def test_file_workflow_search(self, temp_dir):
        """Test search in files."""
        create_tool = CreateFileTool()
        search_tool = SearchTool()

        # Create test files
        file1_path = "test_temp_file1.txt"
        file2_path = "test_temp_file2.txt"

        content1 = "UniqueTestPhrase12345 is great\nJavaScript is also good\nRust is fast"
        content2 = "UniqueTestPhrase12345 programming\nData science with UniqueTestPhrase12345"

        create_tool.execute_sync(path=file1_path, content=content1)
        create_tool.execute_sync(path=file2_path, content=content2)

        # Search for "UniqueTestPhrase12345"
        search_result = search_tool.execute_sync(query="UniqueTestPhrase12345", search_type="text", exclude_pattern="**/test_*.py")
        assert search_result.success is True
        assert len(search_result.data['results']) == 3  # 2 in file1, 1 in file2

        # Search in file names
        file_search_result = search_tool.execute_sync(query="test_temp_file1", search_type="files")
        assert file_search_result.success is True
        assert len(file_search_result.data['results']) == 1
        assert file_search_result.data['results'][0]['match'] == "test_temp_file1.txt"

        # Clean up
        import os
        os.remove(file1_path)
        os.remove(file2_path)

    def test_file_workflow_replace(self, temp_dir):
        """Test text replacement."""
        create_tool = CreateFileTool()
        replace_tool = StrReplaceEditorTool()
        view_tool = ViewFileTool()

        file_path = temp_dir / "replace_test.txt"
        original_content = "The quick brown fox jumps over the lazy dog.\nThe fox is quick."
        create_tool.execute_sync(path=str(file_path), content=original_content)

        # Replace single occurrence
        replace_result = replace_tool.execute_sync(
            path=str(file_path),
            old_str="fox",
            new_str="cat"
        )
        assert replace_result.success is True
        assert replace_result.data['replacements_made'] == 1

        # Check content
        view_result = view_tool.execute_sync(path=str(file_path))
        expected_content = "The quick brown cat jumps over the lazy dog.\nThe fox is quick."
        assert view_result.data['content'] == expected_content

        # Replace all
        replace_all_result = replace_tool.execute_sync(
            path=str(file_path),
            old_str="The",
            new_str="A",
            replace_all=True
        )
        assert replace_all_result.success is True
        assert replace_all_result.data['replacements_made'] == 2

        # Check final content
        final_view = view_tool.execute_sync(path=str(file_path))
        expected_final = "A quick brown cat jumps over the lazy dog.\nA fox is quick."
        assert final_view.data['content'] == expected_final

    def test_file_workflow_directory(self, temp_dir):
        """Test directory operations."""
        create_tool = CreateFileTool()
        view_tool = ViewFileTool()

        # Create directory structure
        sub_dir = temp_dir / "subdir"
        sub_dir.mkdir()

        file1 = temp_dir / "file1.txt"
        file2 = sub_dir / "file2.txt"

        create_tool.execute_sync(path=str(file1), content="content1")
        create_tool.execute_sync(path=str(file2), content="content2")

        # View directory
        dir_result = view_tool.execute_sync(path=str(temp_dir))
        assert dir_result.success is True
        assert dir_result.data['type'] == "directory"
        assert len(dir_result.data['contents']) == 2  # file1.txt and subdir

        names = [item['name'] for item in dir_result.data['contents']]
        assert "file1.txt" in names
        assert "subdir" in names

        # View subdirectory
        sub_dir_result = view_tool.execute_sync(path=str(sub_dir))
        assert sub_dir_result.success is True
        assert len(sub_dir_result.data['contents']) == 1
        assert sub_dir_result.data['contents'][0]['name'] == "file2.txt"