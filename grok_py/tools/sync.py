"""File synchronization tools for Grok CLI."""

import asyncio
import hashlib
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from grok_py.tools.base import SyncTool, AsyncTool, ToolCategory, ToolResult, register_tool
from grok_py.ui.components.progress import ProgressIndicator


class SyncAction(Enum):
    """Synchronization actions."""
    COPY_TO_DEST = "copy_to_dest"
    COPY_TO_SOURCE = "copy_to_source"
    DELETE_FROM_DEST = "delete_from_dest"
    DELETE_FROM_SOURCE = "delete_from_source"
    CONFLICT = "conflict"


@dataclass
class FileInfo:
    """File information for comparison."""
    path: Path
    size: int
    mtime: float
    hash: Optional[str] = None

    def __post_init__(self):
        if self.hash is None:
            self.hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        """Calculate file hash."""
        try:
            hash_obj = hashlib.md5()
            with open(self.path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except (OSError, IOError):
            return ""


@dataclass
class SyncItem:
    """Item to synchronize."""
    relative_path: str
    source_info: Optional[FileInfo]
    dest_info: Optional[FileInfo]
    action: SyncAction
    reason: str


class DirectorySyncHelper:
    """Helper class for directory synchronization."""

    @staticmethod
    def scan_directory(directory: Path, recursive: bool = True) -> Dict[str, FileInfo]:
        """Scan directory and return file information."""
        files = {}
        try:
            if recursive:
                for file_path in directory.rglob('*'):
                    if file_path.is_file():
                        rel_path = str(file_path.relative_to(directory))
                        files[rel_path] = FileInfo(
                            path=file_path,
                            size=file_path.stat().st_size,
                            mtime=file_path.stat().st_mtime
                        )
            else:
                for file_path in directory.iterdir():
                    if file_path.is_file():
                        rel_path = str(file_path.relative_to(directory))
                        files[rel_path] = FileInfo(
                            path=file_path,
                            size=file_path.stat().st_size,
                            mtime=file_path.stat().st_mtime
                        )
        except OSError as e:
            logging.warning(f"Error scanning directory {directory}: {e}")

        return files

    @staticmethod
    def compare_directories(source_files: Dict[str, FileInfo],
                          dest_files: Dict[str, FileInfo],
                          compare_method: str = "hash") -> List[SyncItem]:
        """Compare two directory scans and return sync items."""
        sync_items = []

        # Files in source but not in dest
        for rel_path, source_info in source_files.items():
            if rel_path not in dest_files:
                sync_items.append(SyncItem(
                    relative_path=rel_path,
                    source_info=source_info,
                    dest_info=None,
                    action=SyncAction.COPY_TO_DEST,
                    reason="File exists only in source"
                ))

        # Files in dest but not in source
        for rel_path, dest_info in dest_files.items():
            if rel_path not in source_files:
                sync_items.append(SyncItem(
                    relative_path=rel_path,
                    source_info=None,
                    dest_info=dest_info,
                    action=SyncAction.DELETE_FROM_DEST,
                    reason="File exists only in destination"
                ))

        # Files in both - check for differences
        for rel_path in set(source_files.keys()) & set(dest_files.keys()):
            source_info = source_files[rel_path]
            dest_info = dest_files[rel_path]

            needs_sync = False
            reason = ""

            if compare_method == "hash":
                if source_info.hash != dest_info.hash:
                    needs_sync = True
                    reason = "File contents differ"
            elif compare_method == "mtime":
                if source_info.mtime > dest_info.mtime:
                    needs_sync = True
                    reason = "Source file is newer"
                elif dest_info.mtime > source_info.mtime:
                    needs_sync = True
                    reason = "Destination file is newer"
            elif compare_method == "size":
                if source_info.size != dest_info.size:
                    needs_sync = True
                    reason = "File sizes differ"

            if needs_sync:
                if compare_method == "mtime":
                    if source_info.mtime > dest_info.mtime:
                        action = SyncAction.COPY_TO_DEST
                    else:
                        action = SyncAction.COPY_TO_SOURCE
                else:
                    # For hash/size comparison, prefer source
                    action = SyncAction.COPY_TO_DEST

                sync_items.append(SyncItem(
                    relative_path=rel_path,
                    source_info=source_info,
                    dest_info=dest_info,
                    action=action,
                    reason=reason
                ))

        return sync_items


@register_tool(category=ToolCategory.FILE_OPERATION, name="compare_directories",
               description="Compare two directories and identify differences")
class CompareDirectoriesTool(SyncTool):
    """Tool for comparing directories."""

    def execute_sync(self, source_dir: str, dest_dir: str,
                    compare_method: str = "hash", recursive: bool = True) -> ToolResult:
        """Compare two directories.

        Args:
            source_dir: Source directory path
            dest_dir: Destination directory path
            compare_method: Method to compare files (hash, mtime, size)
            recursive: Whether to compare recursively

        Returns:
            ToolResult: Comparison results
        """
        try:
            source_path = Path(source_dir)
            dest_path = Path(dest_dir)

            if not source_path.exists() or not source_path.is_dir():
                return ToolResult(success=False, error=f"Source directory does not exist: {source_dir}")

            if not dest_path.exists() or not dest_path.is_dir():
                return ToolResult(success=False, error=f"Destination directory does not exist: {dest_dir}")

            # Scan directories
            source_files = DirectorySyncHelper.scan_directory(source_path, recursive)
            dest_files = DirectorySyncHelper.scan_directory(dest_path, recursive)

            # Compare
            sync_items = DirectorySyncHelper.compare_directories(source_files, dest_files, compare_method)

            # Group results
            copy_to_dest = [item for item in sync_items if item.action == SyncAction.COPY_TO_DEST]
            copy_to_source = [item for item in sync_items if item.action == SyncAction.COPY_TO_SOURCE]
            delete_from_dest = [item for item in sync_items if item.action == SyncAction.DELETE_FROM_DEST]
            conflicts = [item for item in sync_items if item.action == SyncAction.CONFLICT]

            return ToolResult(success=True, data={
                "source_directory": str(source_path),
                "dest_directory": str(dest_path),
                "comparison_method": compare_method,
                "recursive": recursive,
                "copy_to_dest": len(copy_to_dest),
                "copy_to_source": len(copy_to_source),
                "delete_from_dest": len(delete_from_dest),
                "conflicts": len(conflicts),
                "total_changes": len(sync_items),
                "details": {
                    "copy_to_dest_items": [{"path": item.relative_path, "reason": item.reason} for item in copy_to_dest],
                    "copy_to_source_items": [{"path": item.relative_path, "reason": item.reason} for item in copy_to_source],
                    "delete_from_dest_items": [{"path": item.relative_path, "reason": item.reason} for item in delete_from_dest],
                    "conflict_items": [{"path": item.relative_path, "reason": item.reason} for item in conflicts]
                }
            })

        except Exception as e:
            return ToolResult(success=False, error=f"Directory comparison failed: {str(e)}")


@register_tool(category=ToolCategory.FILE_OPERATION, name="sync_directories",
               description="Synchronize two directories bidirectionally with progress tracking")
class SyncDirectoriesTool(AsyncTool):
    """Tool for synchronizing directories."""

    async def execute(self, source_dir: str, dest_dir: str,
                     sync_mode: str = "bidirectional", compare_method: str = "hash",
                     recursive: bool = True, dry_run: bool = False,
                     delete_extra: bool = False) -> ToolResult:
        """Synchronize two directories.

        Args:
            source_dir: Source directory path
            dest_dir: Destination directory path
            sync_mode: Sync mode (bidirectional, source_to_dest, dest_to_source)
            compare_method: Method to compare files (hash, mtime, size)
            recursive: Whether to sync recursively
            dry_run: Preview changes without executing
            delete_extra: Whether to delete files that don't exist in source

        Returns:
            ToolResult: Synchronization results
        """
        try:
            source_path = Path(source_dir)
            dest_path = Path(dest_dir)

            if not source_path.exists() or not source_path.is_dir():
                return ToolResult(success=False, error=f"Source directory does not exist: {source_dir}")

            if not dest_path.exists():
                dest_path.mkdir(parents=True, exist_ok=True)

            # Scan directories
            source_files = DirectorySyncHelper.scan_directory(source_path, recursive)
            dest_files = DirectorySyncHelper.scan_directory(dest_path, recursive)

            # Compare
            sync_items = DirectorySyncHelper.compare_directories(source_files, dest_files, compare_method)

            # Filter based on sync mode
            if sync_mode == "source_to_dest":
                sync_items = [item for item in sync_items if item.action in [SyncAction.COPY_TO_DEST]]
                if delete_extra:
                    sync_items.extend([item for item in sync_items if item.action == SyncAction.DELETE_FROM_DEST])
            elif sync_mode == "dest_to_source":
                sync_items = [item for item in sync_items if item.action in [SyncAction.COPY_TO_SOURCE]]
                if delete_extra:
                    sync_items.extend([item for item in sync_items if item.action == SyncAction.DELETE_FROM_SOURCE])
            # For bidirectional, keep all items

            progress = ProgressIndicator()
            callback = ProgressCallback(progress)
            task_id = progress.start_task("Directory synchronization", total=len(sync_items))

            copied_files = []
            deleted_files = []
            errors = []

            for i, item in enumerate(sync_items):
                if callback.cancelled:
                    break

                try:
                    if item.action == SyncAction.COPY_TO_DEST:
                        source_file = source_path / item.relative_path
                        dest_file = dest_path / item.relative_path
                        dest_file.parent.mkdir(parents=True, exist_ok=True)

                        if not dry_run:
                            shutil.copy2(str(source_file), str(dest_file))
                        copied_files.append(str(item.relative_path))

                    elif item.action == SyncAction.COPY_TO_SOURCE:
                        dest_file = dest_path / item.relative_path
                        source_file = source_path / item.relative_path
                        source_file.parent.mkdir(parents=True, exist_ok=True)

                        if not dry_run:
                            shutil.copy2(str(dest_file), str(source_file))
                        copied_files.append(str(item.relative_path))

                    elif item.action in [SyncAction.DELETE_FROM_DEST, SyncAction.DELETE_FROM_SOURCE]:
                        if item.action == SyncAction.DELETE_FROM_DEST:
                            file_to_delete = dest_path / item.relative_path
                        else:
                            file_to_delete = source_path / item.relative_path

                        if not dry_run:
                            file_to_delete.unlink()
                        deleted_files.append(str(item.relative_path))

                except Exception as e:
                    errors.append(f"Failed to sync {item.relative_path}: {str(e)}")

                callback.update(i + 1, len(sync_items), f"Processing {item.relative_path}")

            progress.complete_task(task_id)

            result_data = {
                "source_directory": str(source_path),
                "dest_directory": str(dest_path),
                "sync_mode": sync_mode,
                "comparison_method": compare_method,
                "recursive": recursive,
                "dry_run": dry_run,
                "copied_files": copied_files,
                "deleted_files": deleted_files,
                "errors": errors,
                "total_processed": len(sync_items)
            }

            if errors:
                return ToolResult(success=False, error=f"Synchronization completed with {len(errors)} errors",
                                 data=result_data)
            else:
                return ToolResult(success=True, data=result_data)

        except Exception as e:
            return ToolResult(success=False, error=f"Directory synchronization failed: {str(e)}")


@register_tool(category=ToolCategory.FILE_OPERATION, name="sync_status",
               description="Check synchronization status between two directories")
class SyncStatusTool(SyncTool):
    """Tool for checking sync status."""

    def execute_sync(self, source_dir: str, dest_dir: str,
                    compare_method: str = "hash", recursive: bool = True) -> ToolResult:
        """Check sync status between directories.

        Args:
            source_dir: Source directory path
            dest_dir: Destination directory path
            compare_method: Method to compare files
            recursive: Whether to check recursively

        Returns:
            ToolResult: Sync status
        """
        try:
            # Use the compare tool to get status
            compare_tool = CompareDirectoriesTool()
            result = compare_tool.execute_sync(source_dir, dest_dir, compare_method, recursive)

            if not result.success:
                return result

            data = result.data
            total_changes = data["total_changes"]

            if total_changes == 0:
                status = "synchronized"
                message = "Directories are synchronized"
            else:
                status = "out_of_sync"
                message = f"Directories are out of sync: {total_changes} differences found"

            data["status"] = status
            data["message"] = message

            return ToolResult(success=True, data=data)

        except Exception as e:
            return ToolResult(success=False, error=f"Sync status check failed: {str(e)}")


@register_tool(category=ToolCategory.FILE_OPERATION, name="backup_directory",
               description="Create a backup of a directory before synchronization")
class BackupDirectoryTool(AsyncTool):
    """Tool for backing up directories."""

    async def execute(self, directory: str, backup_location: Optional[str] = None,
                     backup_name: Optional[str] = None) -> ToolResult:
        """Create a backup of a directory.

        Args:
            directory: Directory to backup
            backup_location: Location for backup (optional)
            backup_name: Name for backup archive (optional)

        Returns:
            ToolResult: Backup result
        """
        try:
            source_path = Path(directory)
            if not source_path.exists() or not source_path.is_dir():
                return ToolResult(success=False, error=f"Directory does not exist: {directory}")

            # Determine backup location
            if backup_location:
                backup_dir = Path(backup_location)
            else:
                backup_dir = source_path.parent / "backups"

            backup_dir.mkdir(parents=True, exist_ok=True)

            # Generate backup name
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            dir_name = source_path.name
            if backup_name:
                archive_name = f"{backup_name}_{timestamp}"
            else:
                archive_name = f"{dir_name}_backup_{timestamp}"

            archive_path = backup_dir / f"{archive_name}.tar.gz"

            # Create compressed archive
            import tarfile
            progress = ProgressIndicator()
            task_id = progress.start_task("Creating backup", total=1)

            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(str(source_path), arcname=source_path.name)

            progress.complete_task(task_id)

            return ToolResult(success=True, data={
                "source_directory": str(source_path),
                "backup_path": str(archive_path),
                "backup_size": archive_path.stat().st_size,
                "message": f"Backup created successfully at {archive_path}"
            })

        except Exception as e:
            return ToolResult(success=False, error=f"Backup creation failed: {str(e)}")