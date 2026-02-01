"""Unit tests for file operation tools."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from grok_py.tools.file_tools import ViewFileTool


class TestViewFileTool:
    """Test suite for ViewFileTool."""

    @pytest.fixture
    def view_file_tool(self):
        """Fixture to create a ViewFileTool instance."""
        return ViewFileTool()

    def test_view_file_all_lines(self, view_file_tool):
        """Test viewing entire file content."""
        # Mock file content
        mock_lines = ["line 1\n", "line 2\n", "line 3\n"]
        expected_content = "line 1\nline 2\nline 3\n"

        with patch('builtins.open') as mock_open:
            mock_file = MagicMock()
            mock_file.readlines.return_value = mock_lines
            mock_open.return_value.__enter__.return_value = mock_file

            with patch('grok_py.tools.file_tools.Path') as mock_path_class:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.is_dir.return_value = False
                mock_path_class.return_value = mock_path

                result = view_file_tool.execute_sync(path="test.txt")

                assert result.success is True
                assert result.data['type'] == "file"
                assert result.data['path'] == "test.txt"
                assert result.data['content'] == expected_content
                assert result.data['line_info'] == "All 3 lines"
                assert result.data['total_lines'] == 3
                assert result.error is None

    def test_view_file_partial_lines(self, view_file_tool):
        """Test viewing partial file content with start_line and end_line."""
        mock_lines = ["line 1\n", "line 2\n", "line 3\n", "line 4\n", "line 5\n"]
        expected_content = "line 2\nline 3\n"

        with patch('builtins.open') as mock_open:
            mock_file = MagicMock()
            mock_file.readlines.return_value = mock_lines
            mock_open.return_value.__enter__.return_value = mock_file

            with patch('grok_py.tools.file_tools.Path') as mock_path_class:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.is_dir.return_value = False
                mock_path_class.return_value = mock_path

                result = view_file_tool.execute_sync(path="test.txt", start_line=2, end_line=3)

                assert result.success is True
                assert result.data['content'] == expected_content
                assert result.data['line_info'] == "Lines 2-3 of 5"
                assert result.data['total_lines'] == 5

    def test_view_file_invalid_range(self, view_file_tool):
        """Test invalid line range handling."""
        mock_lines = ["line 1\n", "line 2\n"]

        with patch('builtins.open') as mock_open:
            mock_file = MagicMock()
            mock_file.readlines.return_value = mock_lines
            mock_open.return_value.__enter__.return_value = mock_file

            with patch('grok_py.tools.file_tools.Path') as mock_path_class:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.is_dir.return_value = False
                mock_path_class.return_value = mock_path

                # Invalid: start > end
                result = view_file_tool.execute_sync(path="test.txt", start_line=3, end_line=2)

                assert result.success is False
                assert "Invalid line range" in result.error
                assert result.data['total_lines'] == 2

    def test_view_directory(self, view_file_tool):
        """Test directory listing."""
        with patch('grok_py.tools.file_tools.Path') as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.is_dir.return_value = True

            mock_item1 = MagicMock()
            mock_item1.name = "file1.txt"
            mock_item1.is_dir.return_value = False
            mock_item1.__str__ = MagicMock(return_value="test_dir/file1.txt")

            mock_item2 = MagicMock()
            mock_item2.name = "dir1"
            mock_item2.is_dir.return_value = True
            mock_item2.__str__ = MagicMock(return_value="test_dir/dir1")

            mock_path.iterdir.return_value = [mock_item1, mock_item2]
            mock_path_class.return_value = mock_path

            result = view_file_tool.execute_sync(path="test_dir")

            assert result.success is True
            assert result.data['type'] == "directory"
            assert len(result.data['contents']) == 2
            assert result.data['contents'][0]['name'] == "dir1"
            assert result.data['contents'][0]['type'] == "directory"
            assert result.data['contents'][1]['name'] == "file1.txt"
            assert result.data['contents'][1]['type'] == "file"

    def test_view_directory_permission_denied(self, view_file_tool):
        """Test permission denied on directory."""
        with patch('grok_py.tools.file_tools.Path') as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.is_dir.return_value = True
            mock_path.iterdir.side_effect = PermissionError("Permission denied")
            mock_path_class.return_value = mock_path

            result = view_file_tool.execute_sync(path="test_dir")

            assert result.success is False
            assert "Permission denied" in result.error

    def test_view_file_permission_denied(self, view_file_tool):
        """Test permission denied on file."""
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with patch('grok_py.tools.file_tools.Path') as mock_path_class:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.is_dir.return_value = False
                mock_path_class.return_value = mock_path

                result = view_file_tool.execute_sync(path="test.txt")

                assert result.success is False
                assert "Permission denied" in result.error

    def test_view_binary_file(self, view_file_tool):
        """Test binary file (UnicodeDecodeError)."""
        with patch('builtins.open', side_effect=UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid')):
            with patch('grok_py.tools.file_tools.Path') as mock_path_class:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.is_dir.return_value = False
                mock_path_class.return_value = mock_path

                result = view_file_tool.execute_sync(path="binary.dat")

                assert result.success is False
                assert "Cannot read file as text (binary file)" in result.error

    def test_view_path_not_exist(self, view_file_tool):
        """Test non-existent path."""
        with patch('grok_py.tools.file_tools.Path') as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_path_class.return_value = mock_path

            result = view_file_tool.execute_sync(path="nonexistent.txt")

            assert result.success is False
            assert "Path does not exist" in result.error

    def test_view_unexpected_exception(self, view_file_tool):
        """Test unexpected exceptions."""
        with patch('grok_py.tools.file_tools.Path', side_effect=Exception("Unexpected error")):
            result = view_file_tool.execute_sync(path="test.txt")

            assert result.success is False
            assert "Unexpected error" in result.error


class TestCreateFileTool:
    """Test suite for CreateFileTool."""

    @pytest.fixture
    def create_file_tool(self):
        """Fixture to create a CreateFileTool instance."""
        from grok_py.tools.file_tools import CreateFileTool
        return CreateFileTool()

    def test_create_file_success(self, create_file_tool):
        """Test successful file creation."""
        content = "Hello, world!"

        with patch('builtins.open') as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            with patch('grok_py.tools.file_tools.Path') as mock_path_class:
                mock_path = MagicMock()
                mock_path.exists.return_value = False
                mock_parent = MagicMock()
                mock_path.parent = mock_parent
                mock_path_class.return_value = mock_path

                result = create_file_tool.execute_sync(path="new_file.txt", content=content)

                assert result.success is True
                assert result.data['path'] == "new_file.txt"
                assert result.data['content_length'] == len(content)
                assert "File created successfully" in result.data['message']
                assert result.error is None

                # Verify parent.mkdir was called
                mock_parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
                # Verify open was called with 'w'
                mock_open.assert_called_once_with("new_file.txt", 'w', encoding='utf-8')
                # Verify write was called
                mock_file.write.assert_called_once_with(content)

    def test_create_file_already_exists(self, create_file_tool):
        """Test file already exists error."""
        with patch('grok_py.tools.file_tools.Path') as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path_class.return_value = mock_path

            result = create_file_tool.execute_sync(path="existing_file.txt", content="content")

            assert result.success is False
            assert "File already exists" in result.error
            assert result.data['path'] == "existing_file.txt"

    def test_create_file_permission_denied(self, create_file_tool):
        """Test permission denied."""
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with patch('grok_py.tools.file_tools.Path') as mock_path_class:
                mock_path = MagicMock()
                mock_path.exists.return_value = False
                mock_parent = MagicMock()
                mock_path.parent = mock_parent
                mock_path_class.return_value = mock_path

                result = create_file_tool.execute_sync(path="no_perm.txt", content="content")

                assert result.success is False
                assert "Permission denied" in result.error

    def test_create_file_other_exception(self, create_file_tool):
        """Test other exceptions."""
        with patch('grok_py.tools.file_tools.Path', side_effect=Exception("Some error")):
            result = create_file_tool.execute_sync(path="error.txt", content="content")

            assert result.success is False
            assert "Error creating file: Some error" in result.error


class TestStrReplaceEditorTool:
    """Test suite for StrReplaceEditorTool."""

    @pytest.fixture
    def str_replace_tool(self):
        """Fixture to create a StrReplaceEditorTool instance."""
        from grok_py.tools.file_tools import StrReplaceEditorTool
        return StrReplaceEditorTool()

    def test_replace_success_single(self, str_replace_tool):
        """Test successful single replacement."""
        old_content = "Hello world"
        new_content = "Hello universe"

        with patch('builtins.open') as mock_open:
            mock_file_read = MagicMock()
            mock_file_read.read.return_value = old_content
            mock_file_write = MagicMock()
            mock_open.side_effect = [mock_file_read, mock_file_write]

            with patch('grok_py.tools.file_tools.Path') as mock_path_class:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.is_file.return_value = True
                mock_path_class.return_value = mock_path

                result = str_replace_tool.execute_sync(path="test.txt", old_str="world", new_str="universe")

                assert result.success is True
                assert result.data['replacements_made'] == 1
                assert "Successfully replaced 1 occurrence" in result.data['message']

                # Verify write was called with new content
                mock_file_write.write.assert_called_once_with(new_content)

    def test_replace_success_all(self, str_replace_tool):
        """Test successful replace all."""
        old_content = "foo bar foo baz"
        new_content = "qux bar qux baz"

        with patch('builtins.open') as mock_open:
            mock_file_read = MagicMock()
            mock_file_read.read.return_value = old_content
            mock_file_write = MagicMock()
            mock_open.side_effect = [mock_file_read, mock_file_write]

            with patch('grok_py.tools.file_tools.Path') as mock_path_class:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.is_file.return_value = True
                mock_path_class.return_value = mock_path

                result = str_replace_tool.execute_sync(path="test.txt", old_str="foo", new_str="qux", replace_all=True)

                assert result.success is True
                assert result.data['replacements_made'] == 2

                mock_file_write.write.assert_called_once_with(new_content)

    def test_replace_file_not_exist(self, str_replace_tool):
        """Test file does not exist."""
        with patch('grok_py.tools.file_tools.Path') as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_path_class.return_value = mock_path

            result = str_replace_tool.execute_sync(path="nonexistent.txt", old_str="old", new_str="new")

            assert result.success is False
            assert "File does not exist" in result.error

    def test_replace_not_a_file(self, str_replace_tool):
        """Test path is not a file."""
        with patch('grok_py.tools.file_tools.Path') as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.is_file.return_value = False
            mock_path_class.return_value = mock_path

            result = str_replace_tool.execute_sync(path="directory", old_str="old", new_str="new")

            assert result.success is False
            assert "Path is not a file" in result.error

    def test_replace_binary_file(self, str_replace_tool):
        """Test binary file."""
        with patch('builtins.open', side_effect=UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid')):
            with patch('grok_py.tools.file_tools.Path') as mock_path_class:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.is_file.return_value = True
                mock_path_class.return_value = mock_path

                result = str_replace_tool.execute_sync(path="binary.dat", old_str="old", new_str="new")

                assert result.success is False
                assert "Cannot edit binary file" in result.error

    def test_replace_old_str_not_found(self, str_replace_tool):
        """Test old_str not found."""
        content = "Hello world"

        with patch('builtins.open') as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = content
            mock_open.return_value.__enter__.return_value = mock_file

            with patch('grok_py.tools.file_tools.Path') as mock_path_class:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.is_file.return_value = True
                mock_path_class.return_value = mock_path

                result = str_replace_tool.execute_sync(path="test.txt", old_str="notfound", new_str="new")

                assert result.success is False
                assert "Text to replace not found" in result.error

    def test_replace_permission_denied(self, str_replace_tool):
        """Test permission denied."""
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with patch('grok_py.tools.file_tools.Path') as mock_path_class:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.is_file.return_value = True
                mock_path_class.return_value = mock_path

                result = str_replace_tool.execute_sync(path="readonly.txt", old_str="old", new_str="new")

                assert result.success is False
                assert "Permission denied" in result.error

    def test_replace_other_exception(self, str_replace_tool):
        """Test other exceptions."""
        with patch('grok_py.tools.file_tools.Path', side_effect=Exception("Some error")):
            result = str_replace_tool.execute_sync(path="error.txt", old_str="old", new_str="new")

            assert result.success is False
            assert "Error editing file: Some error" in result.error


class TestSearchTool:
    """Test suite for SearchTool."""

    @pytest.fixture
    def search_tool(self):
        """Fixture to create a SearchTool instance."""
        from grok_py.tools.file_tools import SearchTool
        return SearchTool()

    def test_search_text(self, search_tool):
        """Test text search."""
        mock_walk = [
            (".", [], ["file1.txt"]),
        ]

        with patch('os.walk', return_value=mock_walk):
            with patch('builtins.open') as mock_open:
                mock_file = MagicMock()
                mock_file.readlines.return_value = ["line 1", "hello world", "line 3"]
                mock_open.return_value.__enter__.return_value = mock_file

                result = search_tool.execute_sync(query="hello", search_type="text")

                assert result.success is True
                assert len(result.data['results']) == 1
                assert result.data['results'][0]['type'] == "text"
                assert "hello world" in result.data['results'][0]['match']

    def test_search_files(self, search_tool):
        """Test file name search."""
        mock_walk = [
            (".", [], ["hello.txt", "world.py"]),
        ]

        with patch('os.walk', return_value=mock_walk):
            result = search_tool.execute_sync(query="hello", search_type="files")

            assert result.success is True
            assert len(result.data['results']) == 1
            assert result.data['results'][0]['type'] == "file"
            assert result.data['results'][0]['match'] == "hello.txt"

    def test_search_both(self, search_tool):
        """Test both text and file search."""
        mock_walk = [
            (".", [], ["hello.txt"]),
        ]

        with patch('os.walk', return_value=mock_walk):
            with patch('builtins.open') as mock_open:
                mock_file = MagicMock()
                mock_file.readlines.return_value = ["hello world"]
                mock_open.return_value.__enter__.return_value = mock_file

                result = search_tool.execute_sync(query="hello", search_type="both")

                assert result.success is True
                assert len(result.data['results']) == 2  # one file, one text
                types = [r['type'] for r in result.data['results']]
                assert "file" in types
                assert "text" in types

    def test_search_case_sensitive(self, search_tool):
        """Test case sensitive search."""
        mock_walk = [
            (".", [], ["file.txt"]),
        ]

        with patch('os.walk', return_value=mock_walk):
            with patch('builtins.open') as mock_open:
                mock_file = MagicMock()
                mock_file.readlines.return_value = ["Hello", "hello"]
                mock_open.return_value.__enter__.return_value = mock_file

                result = search_tool.execute_sync(query="Hello", case_sensitive=True, search_type="text")

                assert result.success is True
                assert len(result.data['results']) == 1
                assert "Hello" in result.data['results'][0]['match']

    def test_search_whole_word(self, search_tool):
        """Test whole word search."""
        mock_walk = [
            (".", [], ["file.txt"]),
        ]

        with patch('os.walk', return_value=mock_walk):
            with patch('builtins.open') as mock_open:
                mock_file = MagicMock()
                mock_file.readlines.return_value = ["hello", "helloworld", "hello world"]
                mock_open.return_value.__enter__.return_value = mock_file

                result = search_tool.execute_sync(query="hello", whole_word=True, search_type="text")

                assert result.success is True
                assert len(result.data['results']) == 1
                assert result.data['results'][0]['match'] == "hello"

    def test_search_regex(self, search_tool):
        """Test regex search."""
        mock_walk = [
            (".", [], ["file.txt"]),
        ]

        with patch('os.walk', return_value=mock_walk):
            with patch('builtins.open') as mock_open:
                mock_file = MagicMock()
                mock_file.readlines.return_value = ["test123", "testabc"]
                mock_open.return_value.__enter__.return_value = mock_file

                result = search_tool.execute_sync(query=r"test\d+", regex=True, search_type="text")

                assert result.success is True
                assert len(result.data['results']) == 1
                assert result.data['results'][0]['match'] == "test123"

    def test_search_max_results(self, search_tool):
        """Test max results limit."""
        mock_walk = [
            (".", [], ["file1.txt", "file2.txt"]),
        ]

        with patch('os.walk', return_value=mock_walk):
            with patch('builtins.open') as mock_open:
                mock_file = MagicMock()
                mock_file.readlines.return_value = ["hello"]
                mock_open.return_value.__enter__.return_value = mock_file

                result = search_tool.execute_sync(query="hello", search_type="text", max_results=1)

                assert result.success is True
                assert len(result.data['results']) == 1
                assert result.data['total_results'] == 2  # but limited to 1
                assert result.data['truncated'] is True

    def test_search_file_types(self, search_tool):
        """Test file type filtering."""
        mock_walk = [
            (".", [], ["file.txt", "file.py"]),
        ]

        with patch('os.walk', return_value=mock_walk):
            with patch('builtins.open') as mock_open:
                mock_file = MagicMock()
                mock_file.readlines.return_value = ["hello"]
                mock_open.return_value.__enter__.return_value = mock_file

                result = search_tool.execute_sync(query="hello", search_type="text", file_types=["txt"])

                assert result.success is True
                assert len(result.data['results']) == 1
                assert result.data['results'][0]['path'] == "file.txt"

    def test_search_include_exclude(self, search_tool):
        """Test include/exclude patterns."""
        mock_walk = [
            (".", [], ["include.txt", "exclude.txt"]),
        ]

        with patch('os.walk', return_value=mock_walk):
            with patch('builtins.open') as mock_open:
                mock_file = MagicMock()
                mock_file.readlines.return_value = ["hello"]
                mock_open.return_value.__enter__.return_value = mock_file

                result = search_tool.execute_sync(query="hello", search_type="text", exclude_pattern="exclude*")

                assert result.success is True
                assert len(result.data['results']) == 1
                assert result.data['results'][0]['path'] == "include.txt"

    def test_search_hidden(self, search_tool):
        """Test include hidden files."""
        mock_walk = [
            (".", [".hidden"], [".hidden.txt", "normal.txt"]),
        ]

        with patch('os.walk', return_value=mock_walk):
            result = search_tool.execute_sync(query="hidden", search_type="files", include_hidden=True)

            assert result.success is True
            assert len(result.data['results']) == 1
            assert ".hidden.txt" in result.data['results'][0]['path']

    def test_search_exception(self, search_tool):
        """Test search exception."""
        with patch('os.walk', side_effect=Exception("Walk error")):
            result = search_tool.execute_sync(query="test")

            assert result.success is False
            assert "Search failed" in result.error

    def test_search_no_matches(self, search_tool):
        """Test search with no matches."""
        mock_walk = [
            (".", [], ["file.txt"]),
        ]

        with patch('os.walk', return_value=mock_walk):
            with patch('builtins.open') as mock_open:
                mock_file = MagicMock()
                mock_file.readlines.return_value = ["no match here"]
                mock_open.return_value.__enter__.return_value = mock_file

                result = search_tool.execute_sync(query="hello", search_type="both")

                assert result.success is True
                assert len(result.data['results']) == 0
                assert result.data['total_results'] == 0

    def test_search_binary_file_skip(self, search_tool):
        """Test that binary files are skipped."""
        mock_walk = [
            (".", [], ["text.txt", "binary.bin"]),
        ]

        with patch('os.walk', return_value=mock_walk):
            with patch('builtins.open') as mock_open:
                # Mock text file
                mock_text_file = MagicMock()
                mock_text_file.readlines.return_value = ["hello world"]
                # Mock binary file raises UnicodeDecodeError
                mock_binary_file = MagicMock()
                mock_binary_file.readlines.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")
                mock_open.side_effect = [mock_text_file, mock_binary_file]

                result = search_tool.execute_sync(query="hello", search_type="text")

                assert result.success is True
                assert len(result.data['results']) == 1
                assert result.data['results'][0]['path'] == "text.txt"