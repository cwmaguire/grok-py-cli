"""File operation tools for Grok CLI."""

import os
import logging
import re
import fnmatch
from typing import Optional, List, Dict, Any
from pathlib import Path

from grok_py.tools.base import SyncTool, ToolCategory, ToolResult, register_tool


@register_tool(category=ToolCategory.FILE_OPERATION, name="create_file", description="Create a new file with specified content")
class CreateFileTool(SyncTool):
    """Tool for creating new files with content."""

    def execute_sync(self, path: str, content: str) -> ToolResult:
        """Create a new file with specified content.

        Args:
            path: Path where the file should be created
            content: Content to write to the file

        Returns:
            ToolResult: Success or failure of file creation
        """
        try:
            path_obj = Path(path)

            if path_obj.exists():
                return ToolResult(
                    success=False,
                    error=f"File already exists: {path}",
                    data={"path": path}
                )

            # Create parent directories if they don't exist
            path_obj.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            return ToolResult(
                success=True,
                data={
                    "path": path,
                    "content_length": len(content),
                    "message": f"File created successfully at {path}"
                }
            )

        except PermissionError:
            return ToolResult(
                success=False,
                error=f"Permission denied: {path}",
                data={"path": path}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error creating file: {str(e)}",
                data={"path": path}
            )


@register_tool(category=ToolCategory.FILE_OPERATION, name="view_file", description="View contents of a file or list directory contents")
class ViewFileTool(SyncTool):
    """Tool for viewing file contents or directory listings."""

    def execute_sync(
        self,
        path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None
    ) -> ToolResult:
        """View file contents or directory listing.

        Args:
            path: Path to file or directory to view
            start_line: Starting line number for partial file view (optional)
            end_line: Ending line number for partial file view (optional)

        Returns:
            ToolResult: File contents or directory listing
        """
        try:
            path_obj = Path(path)

            if not path_obj.exists():
                return ToolResult(
                    success=False,
                    error=f"Path does not exist: {path}",
                    data={"path": path}
                )

            if path_obj.is_dir():
                # List directory contents
                contents = []
                try:
                    for item in sorted(path_obj.iterdir()):
                        item_type = "directory" if item.is_dir() else "file"
                        contents.append({
                            "name": item.name,
                            "type": item_type,
                            "path": str(item)
                        })
                except PermissionError:
                    return ToolResult(
                        success=False,
                        error=f"Permission denied: {path}",
                        data={"path": path}
                    )

                return ToolResult(
                    success=True,
                    data={
                        "type": "directory",
                        "path": path,
                        "contents": contents
                    }
                )

            else:
                # Read file contents
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                    total_lines = len(lines)

                    # Handle line ranges
                    if start_line is not None or end_line is not None:
                        start = start_line - 1 if start_line else 0
                        end = end_line if end_line else total_lines

                        # Validate ranges
                        if start < 0 or end > total_lines or start >= end:
                            return ToolResult(
                                success=False,
                                error=f"Invalid line range: start={start_line}, end={end_line}, total_lines={total_lines}",
                                data={"path": path, "total_lines": total_lines}
                            )

                        selected_lines = lines[start:end]
                        content = ''.join(selected_lines)
                        line_info = f"Lines {start+1}-{end} of {total_lines}"
                    else:
                        content = ''.join(lines)
                        line_info = f"All {total_lines} lines"

                    return ToolResult(
                        success=True,
                        data={
                            "type": "file",
                            "path": path,
                            "content": content,
                            "line_info": line_info,
                            "total_lines": total_lines
                        }
                    )

                except UnicodeDecodeError:
                    return ToolResult(
                        success=False,
                        error=f"Cannot read file as text (binary file): {path}",
                        data={"path": path}
                    )
                except PermissionError:
                    return ToolResult(
                        success=False,
                        error=f"Permission denied: {path}",
                        data={"path": path}
                    )
                except Exception as e:
                    return ToolResult(
                        success=False,
                        error=f"Error reading file: {str(e)}",
                        data={"path": path}
                    )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Unexpected error: {str(e)}",
                data={"path": path}
            )


@register_tool(category=ToolCategory.FILE_OPERATION, name="str_replace_editor", description="Replace specific text in a file. Use this for single line edits only")
class StrReplaceEditorTool(SyncTool):
    """Tool for replacing text in existing files."""

    def execute_sync(
        self,
        path: str,
        old_str: str,
        new_str: str,
        replace_all: bool = False
    ) -> ToolResult:
        """Replace specific text in a file.

        Args:
            path: Path to the file to edit
            old_str: Text to replace (must match exactly)
            new_str: Text to replace with
            replace_all: Replace all occurrences (default: false)

        Returns:
            ToolResult: Success or failure of text replacement
        """
        try:
            path_obj = Path(path)

            if not path_obj.exists():
                return ToolResult(
                    success=False,
                    error=f"File does not exist: {path}",
                    data={"path": path}
                )

            if not path_obj.is_file():
                return ToolResult(
                    success=False,
                    error=f"Path is not a file: {path}",
                    data={"path": path}
                )

            # Read the current content
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                return ToolResult(
                    success=False,
                    error=f"Cannot edit binary file: {path}",
                    data={"path": path}
                )

            # Check if old_str exists
            if old_str not in content:
                return ToolResult(
                    success=False,
                    error=f"Text to replace not found in file: '{old_str[:50]}...'",
                    data={"path": path, "old_str_preview": old_str[:100]}
                )

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_str, new_str)
                replacements = content.count(old_str)
            else:
                new_content = content.replace(old_str, new_str, 1)
                replacements = 1

            # Write back the file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return ToolResult(
                success=True,
                data={
                    "path": path,
                    "replacements_made": replacements,
                    "message": f"Successfully replaced {replacements} occurrence(s) in {path}"
                }
            )

        except PermissionError:
            return ToolResult(
                success=False,
                error=f"Permission denied: {path}",
                data={"path": path}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error editing file: {str(e)}",
                data={"path": path}
            )


@register_tool(category=ToolCategory.FILE_OPERATION, name="search", description="Unified search tool for finding text content or files")
class SearchTool(SyncTool):
    """Tool for unified search across files and text content."""

    def execute_sync(
        self,
        query: str,
        search_type: str = "both",
        include_pattern: Optional[str] = None,
        exclude_pattern: Optional[str] = None,
        case_sensitive: bool = False,
        whole_word: bool = False,
        regex: bool = False,
        max_results: int = 50,
        file_types: Optional[List[str]] = None,
        include_hidden: bool = False
    ) -> ToolResult:
        """Unified search for text content or files.

        Args:
            query: Text to search for or file name/path pattern
            search_type: Type of search: 'text', 'files', 'both' (default: 'both')
            include_pattern: Glob pattern for files to include
            exclude_pattern: Glob pattern for files to exclude
            case_sensitive: Whether search should be case sensitive (default: false)
            whole_word: Whether to match whole words only (default: false)
            regex: Whether query is a regex pattern (default: false)
            max_results: Maximum number of results to return (default: 50)
            file_types: File types to search (e.g. ['js', 'ts', 'py'])
            include_hidden: Whether to include hidden files (default: false)

        Returns:
            ToolResult: Search results
        """
        try:
            results = []

            # Prepare regex pattern
            flags = 0 if case_sensitive else re.IGNORECASE
            if regex:
                pattern = re.compile(query, flags)
            else:
                if whole_word:
                    pattern = re.compile(r'\b' + re.escape(query) + r'\b', flags)
                else:
                    pattern = re.compile(re.escape(query), flags)

            # Determine search root (current directory if not specified)
            search_root = Path(".")

            # Walk through files
            for root, dirs, files in os.walk(search_root):
                root_path = Path(root)

                # Skip hidden directories if not including hidden
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith('.')]

                # Process files
                for file in files:
                    file_path = root_path / file

                    # Skip hidden files if not including hidden
                    if not include_hidden and file.startswith('.'):
                        continue

                    # Check file type filter
                    if file_types:
                        file_ext = file_path.suffix.lstrip('.')
                        if file_ext not in file_types:
                            continue

                    # Check include/exclude patterns
                    if include_pattern and not fnmatch.fnmatch(str(file_path), include_pattern):
                        continue
                    if exclude_pattern and fnmatch.fnmatch(str(file_path), exclude_pattern):
                        continue

                    relative_path = str(file_path.relative_to(search_root))

                    # File name search
                    if search_type in ['files', 'both']:
                        if pattern.search(file):
                            results.append({
                                "type": "file",
                                "path": relative_path,
                                "match": file,
                                "line": None,
                                "content": None
                            })
                            if len(results) >= max_results:
                                break

                    # Text content search
                    if search_type in ['text', 'both']:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                lines = f.readlines()

                            for line_num, line in enumerate(lines, 1):
                                if pattern.search(line):
                                    # Get context around the match
                                    start_line = max(1, line_num - 2)
                                    end_line = min(len(lines), line_num + 2)
                                    context_lines = []
                                    for i in range(start_line, end_line + 1):
                                        marker = ">>>" if i == line_num else "   "
                                        context_lines.append(f"{marker} {i:4d}: {lines[i-1].rstrip()}")

                                    results.append({
                                        "type": "text",
                                        "path": relative_path,
                                        "match": line.strip(),
                                        "line": line_num,
                                        "content": "\n".join(context_lines)
                                    })
                                    if len(results) >= max_results:
                                        break
                        except (UnicodeDecodeError, PermissionError):
                            # Skip binary files or inaccessible files
                            continue

                if len(results) >= max_results:
                    break

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": results[:max_results],
                    "total_results": len(results),
                    "max_results": max_results,
                    "truncated": len(results) > max_results
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Search failed: {str(e)}",
                data={"query": query}
            )