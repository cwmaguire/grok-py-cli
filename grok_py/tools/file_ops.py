"""Advanced file operations tools for Grok CLI."""

import asyncio
import hashlib
import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from fnmatch import fnmatch
from concurrent.futures import ThreadPoolExecutor
import tempfile

from grok_py.tools.base import SyncTool, AsyncTool, ToolCategory, ToolResult, register_tool
from grok_py.ui.components.progress import ProgressIndicator


class ProgressCallback:
    """Callback for progress updates."""

    def __init__(self, progress_indicator: Optional[ProgressIndicator] = None,
                 task_id: Optional[str] = None):
        self.progress_indicator = progress_indicator
        self.task_id = task_id
        self.cancelled = False

    def update(self, current: int, total: int, description: str = ""):
        """Update progress."""
        if self.progress_indicator and self.task_id:
            self.progress_indicator.update_task(self.task_id, current, total, description)

    def cancel(self):
        """Cancel the operation."""
        self.cancelled = True


@register_tool(category=ToolCategory.FILE_OPERATION, name="bulk_copy",
               description="Copy multiple files/directories with progress tracking and pattern matching")
class BulkCopyTool(AsyncTool):
    """Tool for bulk copying files and directories."""

    async def execute(self, source_paths: List[str], destination: str,
                     patterns: Optional[List[str]] = None,
                     recursive: bool = True,
                     overwrite: bool = False,
                     dry_run: bool = False) -> ToolResult:
        """Copy multiple files/directories.

        Args:
            source_paths: List of source paths to copy
            destination: Destination directory
            patterns: File patterns to match (e.g., ['*.txt', '*.py'])
            recursive: Whether to copy recursively
            overwrite: Whether to overwrite existing files
            dry_run: Preview operation without executing

        Returns:
            ToolResult: Copy operation results
        """
        try:
            dest_path = Path(destination)
            if not dest_path.exists():
                if not dry_run:
                    dest_path.mkdir(parents=True, exist_ok=True)
            elif not dest_path.is_dir():
                return ToolResult(success=False, error=f"Destination is not a directory: {destination}")

            progress = ProgressIndicator()
            callback = ProgressCallback(progress)
            task_id = progress.start_task("Bulk copy operation", total=len(source_paths))

            copied_files = []
            skipped_files = []
            errors = []

            for i, source in enumerate(source_paths):
                if callback.cancelled:
                    break

                source_path = Path(source)
                if not source_path.exists():
                    errors.append(f"Source does not exist: {source}")
                    continue

                try:
                    await self._copy_item(source_path, dest_path, patterns, recursive,
                                        overwrite, dry_run, callback, copied_files, skipped_files)
                except Exception as e:
                    errors.append(f"Failed to copy {source}: {str(e)}")

                callback.update(i + 1, len(source_paths), f"Processing {source_path.name}")

            progress.complete_task(task_id)

            result_data = {
                "copied": copied_files,
                "skipped": skipped_files,
                "errors": errors,
                "dry_run": dry_run
            }

            if errors:
                return ToolResult(success=False, error=f"Copy completed with {len(errors)} errors",
                                 data=result_data)
            else:
                return ToolResult(success=True, data=result_data)

        except Exception as e:
            return ToolResult(success=False, error=f"Bulk copy failed: {str(e)}")

    async def _copy_item(self, source: Path, dest_dir: Path, patterns: Optional[List[str]],
                        recursive: bool, overwrite: bool, dry_run: bool,
                        callback: ProgressCallback, copied: List[str], skipped: List[str]):
        """Copy a single item (file or directory)."""
        if source.is_file():
            if patterns and not self._matches_patterns(source.name, patterns):
                skipped.append(str(source))
                return

            dest_file = dest_dir / source.name
            if dest_file.exists() and not overwrite:
                skipped.append(str(source))
                return

            if not dry_run:
                shutil.copy2(source, dest_file)
            copied.append(str(source))
        elif source.is_dir() and recursive:
            # For directories, copy matching files recursively
            for file_path in source.rglob('*'):
                if file_path.is_file():
                    if patterns and not self._matches_patterns(file_path.name, patterns):
                        continue

                    # Preserve relative path structure
                    rel_path = file_path.relative_to(source)
                    dest_file = dest_dir / rel_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)

                    if dest_file.exists() and not overwrite:
                        skipped.append(str(file_path))
                        continue

                    if not dry_run:
                        shutil.copy2(file_path, dest_file)
                    copied.append(str(file_path))

    def _matches_patterns(self, filename: str, patterns: List[str]) -> bool:
        """Check if filename matches any of the patterns."""
        return any(fnmatch(filename, pattern) for pattern in patterns)


@register_tool(category=ToolCategory.FILE_OPERATION, name="bulk_move",
               description="Move multiple files/directories with progress tracking")
class BulkMoveTool(AsyncTool):
    """Tool for bulk moving files and directories."""

    async def execute(self, source_paths: List[str], destination: str,
                     overwrite: bool = False, dry_run: bool = False) -> ToolResult:
        """Move multiple files/directories.

        Args:
            source_paths: List of source paths to move
            destination: Destination directory
            overwrite: Whether to overwrite existing files
            dry_run: Preview operation without executing

        Returns:
            ToolResult: Move operation results
        """
        try:
            dest_path = Path(destination)
            if not dest_path.exists():
                if not dry_run:
                    dest_path.mkdir(parents=True, exist_ok=True)
            elif not dest_path.is_dir():
                return ToolResult(success=False, error=f"Destination is not a directory: {destination}")

            progress = ProgressIndicator()
            callback = ProgressCallback(progress)
            task_id = progress.start_task("Bulk move operation", total=len(source_paths))

            moved_files = []
            skipped_files = []
            errors = []

            for i, source in enumerate(source_paths):
                if callback.cancelled:
                    break

                source_path = Path(source)
                if not source_path.exists():
                    errors.append(f"Source does not exist: {source}")
                    continue

                dest_item = dest_path / source_path.name
                if dest_item.exists() and not overwrite:
                    skipped_files.append(str(source))
                    continue

                try:
                    if not dry_run:
                        shutil.move(str(source_path), str(dest_item))
                    moved_files.append(str(source))
                except Exception as e:
                    errors.append(f"Failed to move {source}: {str(e)}")

                callback.update(i + 1, len(source_paths), f"Moving {source_path.name}")

            progress.complete_task(task_id)

            result_data = {
                "moved": moved_files,
                "skipped": skipped_files,
                "errors": errors,
                "dry_run": dry_run
            }

            if errors:
                return ToolResult(success=False, error=f"Move completed with {len(errors)} errors",
                                 data=result_data)
            else:
                return ToolResult(success=True, data=result_data)

        except Exception as e:
            return ToolResult(success=False, error=f"Bulk move failed: {str(e)}")


@register_tool(category=ToolCategory.FILE_OPERATION, name="recursive_delete",
               description="Recursively delete files/directories with pattern matching and safety checks")
class RecursiveDeleteTool(AsyncTool):
    """Tool for recursively deleting files and directories."""

    async def execute(self, paths: List[str], patterns: Optional[List[str]] = None,
                     dry_run: bool = True, force: bool = False) -> ToolResult:
        """Recursively delete files/directories.

        Args:
            paths: List of paths to delete
            patterns: File patterns to match for deletion
            dry_run: Preview operation without executing
            force: Skip confirmation prompts

        Returns:
            ToolResult: Delete operation results
        """
        try:
            progress = ProgressIndicator()
            callback = ProgressCallback(progress)

            # First pass: collect all items to delete
            items_to_delete = []
            for path_str in paths:
                path = Path(path_str)
                if not path.exists():
                    continue

                if path.is_file():
                    if not patterns or self._matches_patterns(path.name, patterns):
                        items_to_delete.append(path)
                elif path.is_dir():
                    for item in path.rglob('*'):
                        if not patterns or self._matches_patterns(item.name, patterns):
                            items_to_delete.append(item)
                    items_to_delete.append(path)  # Add directory itself

            task_id = progress.start_task("Recursive delete operation", total=len(items_to_delete))

            deleted_items = []
            errors = []

            for i, item in enumerate(reversed(items_to_delete)):  # Delete files first, then dirs
                if callback.cancelled:
                    break

                try:
                    if not dry_run:
                        if item.is_dir():
                            item.rmdir()
                        else:
                            item.unlink()
                    deleted_items.append(str(item))
                except Exception as e:
                    errors.append(f"Failed to delete {item}: {str(e)}")

                callback.update(i + 1, len(items_to_delete), f"Deleting {item.name}")

            progress.complete_task(task_id)

            result_data = {
                "deleted": deleted_items,
                "errors": errors,
                "dry_run": dry_run,
                "total_items": len(items_to_delete)
            }

            if errors:
                return ToolResult(success=False, error=f"Delete completed with {len(errors)} errors",
                                 data=result_data)
            else:
                return ToolResult(success=True, data=result_data)

        except Exception as e:
            return ToolResult(success=False, error=f"Recursive delete failed: {str(e)}")

    def _matches_patterns(self, filename: str, patterns: List[str]) -> bool:
        """Check if filename matches any of the patterns."""
        return any(fnmatch(filename, pattern) for pattern in patterns)


@register_tool(category=ToolCategory.FILE_OPERATION, name="find_files",
               description="Find files recursively with advanced pattern matching and filtering")
class FindFilesTool(SyncTool):
    """Tool for finding files with advanced criteria."""

    def execute_sync(self, directory: str, patterns: Optional[List[str]] = None,
                    exclude_patterns: Optional[List[str]] = None,
                    max_depth: Optional[int] = None,
                    min_size: Optional[int] = None,
                    max_size: Optional[int] = None,
                    modified_after: Optional[str] = None,
                    modified_before: Optional[str] = None) -> ToolResult:
        """Find files matching criteria.

        Args:
            directory: Directory to search in
            patterns: File patterns to match (e.g., ['*.py', '*.txt'])
            exclude_patterns: Patterns to exclude
            max_depth: Maximum directory depth
            min_size: Minimum file size in bytes
            max_size: Maximum file size in bytes
            modified_after: Files modified after this date (YYYY-MM-DD)
            modified_before: Files modified before this date (YYYY-MM-DD)

        Returns:
            ToolResult: Found files list
        """
        try:
            search_path = Path(directory)
            if not search_path.exists() or not search_path.is_dir():
                return ToolResult(success=False, error=f"Directory does not exist: {directory}")

            found_files = []

            for root, dirs, files in os.walk(search_path):
                current_depth = len(Path(root).relative_to(search_path).parts)
                if max_depth is not None and current_depth > max_depth:
                    dirs[:] = []  # Don't recurse further
                    continue

                for file in files:
                    file_path = Path(root) / file

                    # Check patterns
                    if patterns and not any(fnmatch(file, pattern) for pattern in patterns):
                        continue

                    if exclude_patterns and any(fnmatch(file, pattern) for pattern in exclude_patterns):
                        continue

                    # Check size
                    try:
                        stat = file_path.stat()
                        if min_size is not None and stat.st_size < min_size:
                            continue
                        if max_size is not None and stat.st_size > max_size:
                            continue

                        # Check modification time
                        if modified_after or modified_before:
                            import datetime
                            mtime = datetime.datetime.fromtimestamp(stat.st_mtime)

                            if modified_after:
                                after_date = datetime.datetime.fromisoformat(modified_after)
                                if mtime < after_date:
                                    continue

                            if modified_before:
                                before_date = datetime.datetime.fromisoformat(modified_before)
                                if mtime > before_date:
                                    continue

                    except OSError:
                        continue  # Skip files we can't stat

                    found_files.append({
                        "path": str(file_path),
                        "relative_path": str(file_path.relative_to(search_path)),
                        "size": file_path.stat().st_size,
                        "modified": file_path.stat().st_mtime
                    })

            return ToolResult(success=True, data={
                "files": found_files,
                "count": len(found_files)
            })

        except Exception as e:
            return ToolResult(success=False, error=f"Find files failed: {str(e)}")


@register_tool(category=ToolCategory.FILE_OPERATION, name="batch_rename",
               description="Batch rename files with pattern replacement and preview")
class BatchRenameTool(SyncTool):
    """Tool for batch renaming files."""

    def execute_sync(self, directory: str, pattern: str, replacement: str,
                    recursive: bool = False, dry_run: bool = True) -> ToolResult:
        """Batch rename files using pattern replacement.

        Args:
            directory: Directory containing files to rename
            pattern: Regex pattern to match in filenames
            replacement: Replacement string
            recursive: Whether to process subdirectories
            dry_run: Preview changes without executing

        Returns:
            ToolResult: Rename operation results
        """
        try:
            import re

            search_path = Path(directory)
            if not search_path.exists() or not search_path.is_dir():
                return ToolResult(success=False, error=f"Directory does not exist: {directory}")

            files_to_rename = []
            if recursive:
                for file_path in search_path.rglob('*'):
                    if file_path.is_file():
                        files_to_rename.append(file_path)
            else:
                for file_path in search_path.iterdir():
                    if file_path.is_file():
                        files_to_rename.append(file_path)

            renamed_files = []
            errors = []

            for file_path in files_to_rename:
                try:
                    new_name = re.sub(pattern, replacement, file_path.name)
                    if new_name != file_path.name:
                        new_path = file_path.parent / new_name
                        if new_path.exists():
                            errors.append(f"Target already exists: {new_path}")
                            continue

                        if not dry_run:
                            file_path.rename(new_path)

                        renamed_files.append({
                            "old_path": str(file_path),
                            "new_path": str(new_path)
                        })

                except Exception as e:
                    errors.append(f"Failed to rename {file_path}: {str(e)}")

            result_data = {
                "renamed": renamed_files,
                "errors": errors,
                "dry_run": dry_run
            }

            if errors:
                return ToolResult(success=False, error=f"Rename completed with {len(errors)} errors",
                                 data=result_data)
            else:
                return ToolResult(success=True, data=result_data)

        except Exception as e:
            return ToolResult(success=False, error=f"Batch rename failed: {str(e)}")