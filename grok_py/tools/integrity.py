"""File integrity verification and repair tools for Grok CLI."""

import asyncio
import hashlib
import logging
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from grok_py.tools.base import SyncTool, AsyncTool, ToolCategory, ToolResult, register_tool
from grok_py.ui.components.progress import ProgressIndicator


@dataclass
class FileChecksum:
    """File checksum information."""
    path: str
    size: int
    mtime: float
    md5: Optional[str] = None
    sha256: Optional[str] = None
    sha1: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "size": self.size,
            "mtime": self.mtime,
            "md5": self.md5,
            "sha256": self.sha256,
            "sha1": self.sha1
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileChecksum':
        """Create from dictionary."""
        return cls(
            path=data["path"],
            size=data["size"],
            mtime=data["mtime"],
            md5=data.get("md5"),
            sha256=data.get("sha256"),
            sha1=data.get("sha1")
        )


class IntegrityHelper:
    """Helper class for integrity operations."""

    @staticmethod
    def calculate_checksum(file_path: Path, algorithms: List[str]) -> Dict[str, str]:
        """Calculate checksums for a file."""
        checksums = {}

        for algorithm in algorithms:
            if algorithm == "md5":
                hash_obj = hashlib.md5()
            elif algorithm == "sha256":
                hash_obj = hashlib.sha256()
            elif algorithm == "sha1":
                hash_obj = hashlib.sha1()
            else:
                continue

            try:
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_obj.update(chunk)
                checksums[algorithm] = hash_obj.hexdigest()
            except (OSError, IOError) as e:
                logging.warning(f"Error calculating {algorithm} for {file_path}: {e}")
                checksums[algorithm] = None

        return checksums

    @staticmethod
    def scan_files(directory: Path, recursive: bool = True,
                  include_patterns: Optional[List[str]] = None,
                  exclude_patterns: Optional[List[str]] = None) -> List[Path]:
        """Scan directory for files."""
        from fnmatch import fnmatch

        files = []
        try:
            iterator = directory.rglob('*') if recursive else directory.iterdir()
            for item in iterator:
                if not item.is_file():
                    continue

                filename = item.name

                # Check include patterns
                if include_patterns and not any(fnmatch(filename, pattern) for pattern in include_patterns):
                    continue

                # Check exclude patterns
                if exclude_patterns and any(fnmatch(filename, pattern) for pattern in exclude_patterns):
                    continue

                files.append(item)

        except OSError as e:
            logging.warning(f"Error scanning directory {directory}: {e}")

        return files

    @staticmethod
    def load_checksums(checksum_file: Path) -> Dict[str, FileChecksum]:
        """Load checksums from file."""
        checksums = {}

        try:
            if checksum_file.suffix.lower() == '.json':
                with open(checksum_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data.get('files', []):
                        fc = FileChecksum.from_dict(item)
                        checksums[fc.path] = fc

            elif checksum_file.suffix.lower() == '.csv':
                with open(checksum_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        fc = FileChecksum(
                            path=row['path'],
                            size=int(row.get('size', 0)),
                            mtime=float(row.get('mtime', 0)),
                            md5=row.get('md5'),
                            sha256=row.get('sha256'),
                            sha1=row.get('sha1')
                        )
                        checksums[fc.path] = fc

        except (OSError, IOError, json.JSONDecodeError, csv.Error) as e:
            logging.error(f"Error loading checksums from {checksum_file}: {e}")

        return checksums

    @staticmethod
    def save_checksums(checksums: Dict[str, FileChecksum], output_file: Path):
        """Save checksums to file."""
        try:
            if output_file.suffix.lower() == '.json':
                data = {
                    "files": [fc.to_dict() for fc in checksums.values()]
                }
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

            elif output_file.suffix.lower() == '.csv':
                fieldnames = ['path', 'size', 'mtime', 'md5', 'sha256', 'sha1']
                with open(output_file, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for fc in checksums.values():
                        writer.writerow(fc.to_dict())

        except (OSError, IOError) as e:
            logging.error(f"Error saving checksums to {output_file}: {e}")
            raise


@register_tool(category=ToolCategory.UTILITY, name="calculate_checksums",
               description="Calculate checksums for files (MD5, SHA-256, SHA-1)")
class CalculateChecksumsTool(AsyncTool):
    """Tool for calculating file checksums."""

    async def execute(self, paths: List[str], algorithms: List[str] = None,
                     recursive: bool = True, include_patterns: Optional[List[str]] = None,
                     exclude_patterns: Optional[List[str]] = None,
                     output_file: Optional[str] = None) -> ToolResult:
        """Calculate checksums for files.

        Args:
            paths: List of file/directory paths
            algorithms: Checksum algorithms to use (md5, sha256, sha1)
            recursive: Whether to process directories recursively
            include_patterns: File patterns to include
            exclude_patterns: File patterns to exclude
            output_file: File to save checksums to (JSON/CSV)

        Returns:
            ToolResult: Checksum calculation results
        """
        try:
            if algorithms is None:
                algorithms = ["md5", "sha256"]

            # Validate algorithms
            valid_algorithms = ["md5", "sha256", "sha1"]
            algorithms = [a for a in algorithms if a in valid_algorithms]

            if not algorithms:
                return ToolResult(success=False, error="No valid algorithms specified")

            # Collect all files
            all_files = []
            for path_str in paths:
                path = Path(path_str)
                if not path.exists():
                    continue

                if path.is_file():
                    all_files.append(path)
                elif path.is_dir():
                    all_files.extend(IntegrityHelper.scan_files(path, recursive, include_patterns, exclude_patterns))

            if not all_files:
                return ToolResult(success=False, error="No files found to process")

            progress = ProgressIndicator()
            task_id = progress.start_task("Calculating checksums", total=len(all_files))

            checksums = {}

            # Calculate checksums in parallel using ThreadPoolExecutor
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=min(4, len(all_files))) as executor:
                tasks = []
                for file_path in all_files:
                    task = loop.run_in_executor(executor, self._calculate_single_file, file_path, algorithms)
                    tasks.append(task)

                for i, task in enumerate(asyncio.as_completed(tasks)):
                    file_path, file_checksums = await task
                    rel_path = str(file_path)
                    stat = file_path.stat()

                    fc = FileChecksum(
                        path=rel_path,
                        size=stat.st_size,
                        mtime=stat.st_mtime,
                        **file_checksums
                    )
                    checksums[rel_path] = fc

                    progress.update_task(task_id, i + 1, len(all_files), f"Processed {file_path.name}")

            progress.complete_task(task_id)

            # Save to file if requested
            if output_file:
                output_path = Path(output_file)
                IntegrityHelper.save_checksums(checksums, output_path)

            return ToolResult(success=True, data={
                "files_processed": len(checksums),
                "algorithms": algorithms,
                "checksums": {path: fc.to_dict() for path, fc in checksums.items()},
                "output_file": output_file
            })

        except Exception as e:
            return ToolResult(success=False, error=f"Checksum calculation failed: {str(e)}")

    def _calculate_single_file(self, file_path: Path, algorithms: List[str]) -> Tuple[Path, Dict[str, str]]:
        """Calculate checksums for a single file."""
        checksums = IntegrityHelper.calculate_checksum(file_path, algorithms)
        return file_path, checksums


@register_tool(category=ToolCategory.UTILITY, name="verify_checksums",
               description="Verify file integrity against stored checksums")
class VerifyChecksumsTool(AsyncTool):
    """Tool for verifying file checksums."""

    async def execute(self, checksum_file: str, algorithms: List[str] = None,
                     update_checksums: bool = False) -> ToolResult:
        """Verify checksums against stored values.

        Args:
            checksum_file: File containing stored checksums (JSON/CSV)
            algorithms: Algorithms to verify (if not specified, uses all available)
            update_checksums: Whether to update the checksum file with current values

        Returns:
            ToolResult: Verification results
        """
        try:
            checksum_path = Path(checksum_file)
            if not checksum_path.exists():
                return ToolResult(success=False, error=f"Checksum file does not exist: {checksum_file}")

            # Load stored checksums
            stored_checksums = IntegrityHelper.load_checksums(checksum_path)
            if not stored_checksums:
                return ToolResult(success=False, error="No checksums found in file")

            if algorithms is None:
                # Use all available algorithms from stored data
                algorithms = []
                sample_fc = next(iter(stored_checksums.values()))
                if sample_fc.md5:
                    algorithms.append("md5")
                if sample_fc.sha256:
                    algorithms.append("sha256")
                if sample_fc.sha1:
                    algorithms.append("sha1")

            progress = ProgressIndicator()
            task_id = progress.start_task("Verifying checksums", total=len(stored_checksums))

            verified = []
            failed = []
            missing = []
            updated = []

            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=min(4, len(stored_checksums))) as executor:
                tasks = []
                for rel_path, stored_fc in stored_checksums.items():
                    task = loop.run_in_executor(executor, self._verify_single_file,
                                              rel_path, stored_fc, algorithms)
                    tasks.append(task)

                for i, task in enumerate(asyncio.as_completed(tasks)):
                    rel_path, result = await task

                    if result["status"] == "verified":
                        verified.append(result)
                    elif result["status"] == "failed":
                        failed.append(result)
                        if update_checksums:
                            updated.append(rel_path)
                    elif result["status"] == "missing":
                        missing.append(result)
                        if update_checksums:
                            stored_checksums.pop(rel_path, None)

                    progress.update_task(task_id, i + 1, len(stored_checksums), f"Verified {Path(rel_path).name}")

            progress.complete_task(task_id)

            # Update checksum file if requested
            if update_checksums and (updated or missing):
                IntegrityHelper.save_checksums(stored_checksums, checksum_path)

            result_data = {
                "total_files": len(stored_checksums),
                "verified": len(verified),
                "failed": len(failed),
                "missing": len(missing),
                "algorithms": algorithms,
                "details": {
                    "verified": verified,
                    "failed": failed,
                    "missing": missing
                },
                "checksums_updated": update_checksums
            }

            if failed or missing:
                return ToolResult(success=False, error=f"Verification failed: {len(failed)} failed, {len(missing)} missing",
                                 data=result_data)
            else:
                return ToolResult(success=True, data=result_data)

        except Exception as e:
            return ToolResult(success=False, error=f"Checksum verification failed: {str(e)}")

    def _verify_single_file(self, rel_path: str, stored_fc: FileChecksum,
                           algorithms: List[str]) -> Tuple[str, Dict[str, Any]]:
        """Verify a single file."""
        file_path = Path(rel_path)

        if not file_path.exists():
            return rel_path, {
                "status": "missing",
                "path": rel_path,
                "error": "File does not exist"
            }

        # Check file size and mtime first
        stat = file_path.stat()
        if stat.st_size != stored_fc.size:
            return rel_path, {
                "status": "failed",
                "path": rel_path,
                "error": f"Size mismatch: {stat.st_size} != {stored_fc.size}",
                "expected_size": stored_fc.size,
                "actual_size": stat.st_size
            }

        # Calculate current checksums
        current_checksums = IntegrityHelper.calculate_checksum(file_path, algorithms)

        # Verify each algorithm
        for algorithm in algorithms:
            stored_value = getattr(stored_fc, algorithm)
            current_value = current_checksums.get(algorithm)

            if stored_value and current_value and stored_value != current_value:
                return rel_path, {
                    "status": "failed",
                    "path": rel_path,
                    "algorithm": algorithm,
                    "error": f"{algorithm.upper()} mismatch",
                    "expected": stored_value,
                    "actual": current_value
                }

        return rel_path, {
            "status": "verified",
            "path": rel_path,
            "size": stat.st_size,
            "mtime": stat.st_mtime
        }


@register_tool(category=ToolCategory.UTILITY, name="find_corrupted_files",
               description="Scan directories for corrupted files using checksums")
class FindCorruptedFilesTool(AsyncTool):
    """Tool for finding corrupted files."""

    async def execute(self, directory: str, checksum_file: Optional[str] = None,
                     algorithms: List[str] = None, recursive: bool = True) -> ToolResult:
        """Find corrupted files in directory.

        Args:
            directory: Directory to scan
            checksum_file: Optional checksum file to verify against
            algorithms: Algorithms to use for verification
            recursive: Whether to scan recursively

        Returns:
            ToolResult: Corruption scan results
        """
        try:
            dir_path = Path(directory)
            if not dir_path.exists() or not dir_path.is_dir():
                return ToolResult(success=False, error=f"Directory does not exist: {directory}")

            if algorithms is None:
                algorithms = ["md5"]

            # If checksum file provided, use verify tool
            if checksum_file:
                verify_tool = VerifyChecksumsTool()
                return verify_tool.execute(checksum_file, algorithms, update_checksums=False)

            # Otherwise, scan for obviously corrupted files
            files = IntegrityHelper.scan_files(dir_path, recursive)

            progress = ProgressIndicator()
            task_id = progress.start_task("Scanning for corruption", total=len(files))

            corrupted = []
            suspicious = []

            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=min(4, len(files))) as executor:
                tasks = []
                for file_path in files:
                    task = loop.run_in_executor(executor, self._check_file_integrity, file_path)
                    tasks.append(task)

                for i, task in enumerate(asyncio.as_completed(tasks)):
                    file_path, result = await task

                    if result["status"] == "corrupted":
                        corrupted.append(result)
                    elif result["status"] == "suspicious":
                        suspicious.append(result)

                    progress.update_task(task_id, i + 1, len(files), f"Scanned {file_path.name}")

            progress.complete_task(task_id)

            result_data = {
                "directory": str(dir_path),
                "files_scanned": len(files),
                "corrupted": len(corrupted),
                "suspicious": len(suspicious),
                "details": {
                    "corrupted": corrupted,
                    "suspicious": suspicious
                }
            }

            if corrupted:
                return ToolResult(success=False, error=f"Found {len(corrupted)} corrupted files",
                                 data=result_data)
            else:
                return ToolResult(success=True, data=result_data)

        except Exception as e:
            return ToolResult(success=False, error=f"Corruption scan failed: {str(e)}")

    def _check_file_integrity(self, file_path: Path) -> Tuple[Path, Dict[str, Any]]:
        """Check integrity of a single file."""
        try:
            # Basic checks
            stat = file_path.stat()

            # Check if file size is reasonable
            if stat.st_size == 0:
                return file_path, {
                    "status": "suspicious",
                    "path": str(file_path),
                    "reason": "Empty file",
                    "size": stat.st_size
                }

            # Try to read the file
            try:
                with open(file_path, 'rb') as f:
                    # Read first and last 1KB
                    f.read(1024)
                    if stat.st_size > 2048:
                        f.seek(-1024, 2)
                        f.read(1024)
            except (OSError, IOError) as e:
                return file_path, {
                    "status": "corrupted",
                    "path": str(file_path),
                    "reason": f"Read error: {str(e)}",
                    "size": stat.st_size
                }

            return file_path, {
                "status": "ok",
                "path": str(file_path),
                "size": stat.st_size
            }

        except OSError as e:
            return file_path, {
                "status": "corrupted",
                "path": str(file_path),
                "reason": f"Stat error: {str(e)}"
            }


@register_tool(category=ToolCategory.UTILITY, name="repair_file",
               description="Attempt to repair corrupted files using backup copies")
class RepairFileTool(SyncTool):
    """Tool for repairing corrupted files."""

    def execute_sync(self, corrupted_file: str, backup_file: Optional[str] = None,
                    backup_directory: Optional[str] = None) -> ToolResult:
        """Attempt to repair a corrupted file.

        Args:
            corrupted_file: Path to corrupted file
            backup_file: Specific backup file to use
            backup_directory: Directory to search for backups

        Returns:
            ToolResult: Repair result
        """
        try:
            corrupted_path = Path(corrupted_file)
            if not corrupted_path.exists():
                return ToolResult(success=False, error=f"Corrupted file does not exist: {corrupted_file}")

            backup_candidates = []

            # Specific backup file
            if backup_file:
                backup_path = Path(backup_file)
                if backup_path.exists():
                    backup_candidates.append(backup_path)

            # Search backup directory
            if backup_directory:
                backup_dir = Path(backup_directory)
                if backup_dir.exists() and backup_dir.is_dir():
                    # Look for files with similar names
                    for backup_file in backup_dir.rglob('*'):
                        if backup_file.is_file() and backup_file.name == corrupted_path.name:
                            backup_candidates.append(backup_file)

            if not backup_candidates:
                return ToolResult(success=False, error="No suitable backup files found")

            # Use the first (most recent?) backup
            backup_path = backup_candidates[0]

            # Create backup of corrupted file
            corrupted_backup = corrupted_path.with_suffix(corrupted_path.suffix + '.corrupted')
            if not corrupted_backup.exists():
                import shutil
                shutil.copy2(corrupted_path, corrupted_backup)

            # Replace with backup
            shutil.copy2(backup_path, corrupted_path)

            return ToolResult(success=True, data={
                "corrupted_file": str(corrupted_path),
                "backup_file_used": str(backup_path),
                "corrupted_backup": str(corrupted_backup),
                "message": "File repaired using backup copy"
            })

        except Exception as e:
            return ToolResult(success=False, error=f"File repair failed: {str(e)}")