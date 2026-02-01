"""Unit tests for SearchReplaceTool and related classes."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from grok_py.tools.search_replace import (
    SearchReplaceHelper,
    Replacement,
    SearchResult
)



class TestReplacement:
    """Test Replacement dataclass."""

    def test_init(self):
        """Test Replacement initialization."""
        replacement = Replacement(
            file_path="test.py",
            line_number=10,
            old_text="old",
            new_text="new",
            context_before="before",
            context_after="after"
        )
        assert replacement.file_path == "test.py"
        assert replacement.line_number == 10
        assert replacement.old_text == "old"
        assert replacement.new_text == "new"
        assert replacement.context_before == "before"
        assert replacement.context_after == "after"


class TestSearchResult:
    """Test SearchResult dataclass."""

    def test_init(self):
        """Test SearchResult initialization."""
        result = SearchResult(
            file_path="test.py",
            line_number=5,
            column=10,
            match_text="match",
            context="some context"
        )
        assert result.file_path == "test.py"
        assert result.line_number == 5
        assert result.column == 10
        assert result.match_text == "match"
        assert result.context == "some context"


class TestSearchReplaceHelper:
    """Test SearchReplaceHelper static methods."""

    def test_find_files_basic(self, tmp_path):
        """Test find_files basic functionality."""
        # Create test files
        (tmp_path / "test1.txt").write_text("content1")
        (tmp_path / "test2.py").write_text("content2")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "test3.txt").write_text("content3")

        files = SearchReplaceHelper.find_files(tmp_path)
        file_names = [f.name for f in files]

        assert "test1.txt" in file_names
        assert "test2.py" in file_names
        assert "test3.txt" in file_names

    def test_find_files_with_patterns(self, tmp_path):
        """Test find_files with include patterns."""
        (tmp_path / "test1.txt").write_text("content1")
        (tmp_path / "test2.py").write_text("content2")
        (tmp_path / "test3.txt").write_text("content3")

        files = SearchReplaceHelper.find_files(tmp_path, patterns=["*.py"])
        file_names = [f.name for f in files]

        assert "test2.py" in file_names
        assert "test1.txt" not in file_names
        assert "test3.txt" not in file_names

    def test_find_files_exclude_patterns(self, tmp_path):
        """Test find_files with exclude patterns."""
        (tmp_path / "test1.txt").write_text("content1")
        (tmp_path / "test2.py").write_text("content2")

        files = SearchReplaceHelper.find_files(tmp_path, exclude_patterns=["*.txt"])
        file_names = [f.name for f in files]

        assert "test2.py" in file_names
        assert "test1.txt" not in file_names

    def test_find_files_non_recursive(self, tmp_path):
        """Test find_files non-recursive."""
        (tmp_path / "test1.txt").write_text("content1")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "test2.txt").write_text("content2")

        files = SearchReplaceHelper.find_files(tmp_path, recursive=False)
        file_names = [f.name for f in files]

        assert "test1.txt" in file_names
        assert "test2.txt" not in file_names

    def test_search_in_file_basic(self, tmp_path):
        """Test search_in_file basic functionality."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line 1: hello world\nline 2: hello again\nline 3: goodbye")

        results = SearchReplaceHelper.search_in_file(test_file, "hello")

        assert len(results) == 2
        assert results[0].line_number == 1
        assert results[0].match_text == "hello"
        assert results[1].line_number == 2
        assert results[1].match_text == "hello"

    def test_search_in_file_regex(self, tmp_path):
        """Test search_in_file with regex."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line 1: test123\nline 2: test456\nline 3: other")

        results = SearchReplaceHelper.search_in_file(test_file, r"test\d+", regex=True)

        assert len(results) == 2
        assert results[0].match_text == "test123"
        assert results[1].match_text == "test456"

    def test_search_in_file_case_insensitive(self, tmp_path):
        """Test search_in_file case insensitive."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line 1: Hello\nline 2: hello\nline 3: HELLO")

        results = SearchReplaceHelper.search_in_file(test_file, "hello", case_sensitive=False)

        assert len(results) == 3

    def test_search_in_file_whole_word(self, tmp_path):
        """Test search_in_file whole word."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line 1: hello world\nline 2: helloagain\nline 3: say hello")

        results = SearchReplaceHelper.search_in_file(test_file, "hello", whole_word=True)

        assert len(results) == 2  # "hello" at start and "say hello"
        assert results[0].line_number == 1
        assert results[1].line_number == 3

    def test_replace_in_file_basic(self, tmp_path):
        """Test replace_in_file basic functionality."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line 1: hello world\nline 2: hello again")

        replacements, error = SearchReplaceHelper.replace_in_file(test_file, "hello", "hi")

        assert error == ""
        assert len(replacements) == 2
        assert replacements[0].old_text == "hello"
        assert replacements[0].new_text == "hi"
        assert replacements[1].old_text == "hello"
        assert replacements[1].new_text == "hi"

        # Check file content was updated
        content = test_file.read_text()
        assert "hi world" in content
        assert "hi again" in content

    def test_replace_in_file_dry_run(self, tmp_path):
        """Test replace_in_file dry run."""
        test_file = tmp_path / "test.txt"
        original_content = "line 1: hello world\nline 2: hello again"
        test_file.write_text(original_content)

        replacements, error = SearchReplaceHelper.replace_in_file(test_file, "hello", "hi", dry_run=True)

        assert error == ""
        assert len(replacements) == 2

        # Check file content was NOT updated
        content = test_file.read_text()
        assert content == original_content

    def test_replace_in_file_regex(self, tmp_path):
        """Test replace_in_file with regex."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line 1: test123\nline 2: test456")

        replacements, error = SearchReplaceHelper.replace_in_file(test_file, r"test\d+", "replaced", regex=True)

        assert error == ""
        assert len(replacements) == 2
        assert replacements[0].old_text == "test123"
        assert replacements[0].new_text == "replaced"

    def test_replace_in_file_no_matches(self, tmp_path):
        """Test replace_in_file with no matches."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line 1: hello world")

        replacements, error = SearchReplaceHelper.replace_in_file(test_file, "goodbye", "hi")

        assert error == ""
        assert len(replacements) == 0

    def test_replace_in_file_file_error(self, tmp_path):
        """Test replace_in_file with file error."""
        non_existent = tmp_path / "nonexistent.txt"

        replacements, error = SearchReplaceHelper.replace_in_file(non_existent, "hello", "hi")

        assert len(replacements) == 0
        assert "Error processing" in error


