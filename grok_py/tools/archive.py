"""Archive and compression tools for Grok CLI."""

import asyncio
import logging
import os
import shutil
import zipfile
import tarfile
import gzip
import bz2
import lzma
from pathlib import Path
from typing import List, Dict, Any, Optional
from fnmatch import fnmatch

from grok_py.tools.base import SyncTool, AsyncTool, ToolCategory, ToolResult, register_tool
from grok_py.ui.components.progress import ProgressIndicator


class ArchiveHelper:
    """Helper class for archive operations."""

    @staticmethod
    def detect_archive_type(file_path: Path) -> Optional[str]:
        """Detect archive type from file extension."""
        suffix = file_path.suffix.lower()
        if suffix == '.zip':
            return 'zip'
        elif suffix in ['.tar', '.tgz', '.tar.gz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz']:
            return 'tar'
        elif suffix == '.gz':
            return 'gzip'
        elif suffix == '.bz2':
            return 'bzip2'
        elif suffix == '.xz':
            return 'lzma'
        return None

    @staticmethod
    def get_compression_mode(filename: str) -> str:
        """Get compression mode for tar archives."""
        if filename.endswith('.tar.gz') or filename.endswith('.tgz'):
            return 'gz'
        elif filename.endswith('.tar.bz2') or filename.endswith('.tbz2'):
            return 'bz2'
        elif filename.endswith('.tar.xz') or filename.endswith('.txz'):
            return 'xz'
        else:
            return ''  # uncompressed tar


@register_tool(category=ToolCategory.FILE_OPERATION, name="create_archive",
               description="Create compressed archives (zip, tar, gzip) with progress tracking")
class CreateArchiveTool(AsyncTool):
    """Tool for creating archives."""

    async def execute(self, source_paths: List[str], archive_path: str,
                     archive_type: str = "auto", compression_level: int = 6,
                     exclude_patterns: Optional[List[str]] = None) -> ToolResult:
        """Create an archive from source files/directories.

        Args:
            source_paths: List of files/directories to archive
            archive_path: Path for the archive file
            archive_type: Archive type (zip, tar, gzip, auto)
            compression_level: Compression level (1-9)
            exclude_patterns: Patterns to exclude from archiving

        Returns:
            ToolResult: Archive creation result
        """
        try:
            archive_file = Path(archive_path)

            # Determine archive type
            if archive_type == "auto":
                if archive_file.suffix.lower() == '.zip':
                    archive_type = 'zip'
                else:
                    archive_type = 'tar'

            # Validate source paths
            valid_sources = []
            for source in source_paths:
                source_path = Path(source)
                if not source_path.exists():
                    return ToolResult(success=False, error=f"Source path does not exist: {source}")
                valid_sources.append(source_path)

            progress = ProgressIndicator()
            task_id = progress.start_task("Creating archive", total=len(valid_sources))

            if archive_type == 'zip':
                await self._create_zip_archive(valid_sources, archive_file, compression_level,
                                             exclude_patterns, progress, task_id)
            elif archive_type == 'tar':
                await self._create_tar_archive(valid_sources, archive_file, compression_level,
                                             exclude_patterns, progress, task_id)
            else:
                return ToolResult(success=False, error=f"Unsupported archive type: {archive_type}")

            progress.complete_task(task_id)

            # Get archive info
            archive_size = archive_file.stat().st_size

            return ToolResult(success=True, data={
                "archive_path": str(archive_file),
                "archive_type": archive_type,
                "source_paths": [str(p) for p in valid_sources],
                "archive_size": archive_size,
                "compression_level": compression_level,
                "message": f"Archive created successfully: {archive_file}"
            })

        except Exception as e:
            return ToolResult(success=False, error=f"Archive creation failed: {str(e)}")

    async def _create_zip_archive(self, sources: List[Path], archive_file: Path,
                                 compression_level: int, exclude_patterns: Optional[List[str]],
                                 progress: ProgressIndicator, task_id: str):
        """Create a ZIP archive."""
        compression = zipfile.ZIP_DEFLATED
        with zipfile.ZipFile(archive_file, 'w', compression, compresslevel=compression_level) as zf:
            for i, source in enumerate(sources):
                await self._add_to_zip(zf, source, exclude_patterns)
                progress.update_task(task_id, i + 1, len(sources), f"Adding {source.name}")

    async def _create_tar_archive(self, sources: List[Path], archive_file: Path,
                                 compression_level: int, exclude_patterns: Optional[List[str]],
                                 progress: ProgressIndicator, task_id: str):
        """Create a TAR archive."""
        mode = ArchiveHelper.get_compression_mode(str(archive_file))
        if mode:
            mode = f'w:{mode}'
        else:
            mode = 'w'

        with tarfile.open(archive_file, mode, compresslevel=compression_level) as tf:
            for i, source in enumerate(sources):
                await self._add_to_tar(tf, source, exclude_patterns)
                progress.update_task(task_id, i + 1, len(sources), f"Adding {source.name}")

    async def _add_to_zip(self, zf: zipfile.ZipFile, source: Path,
                         exclude_patterns: Optional[List[str]]):
        """Add files to ZIP archive."""
        if source.is_file():
            if not self._should_exclude(source.name, exclude_patterns):
                zf.write(str(source), source.name)
        elif source.is_dir():
            for file_path in source.rglob('*'):
                if file_path.is_file() and not self._should_exclude(file_path.name, exclude_patterns):
                    arcname = file_path.relative_to(source.parent)
                    zf.write(str(file_path), str(arcname))

    async def _add_to_tar(self, tf: tarfile.TarFile, source: Path,
                         exclude_patterns: Optional[List[str]]):
        """Add files to TAR archive."""
        if source.is_file():
            if not self._should_exclude(source.name, exclude_patterns):
                tf.add(str(source), source.name)
        elif source.is_dir():
            tf.add(str(source), source.name, exclude=self._should_exclude_tar)

    def _should_exclude(self, filename: str, patterns: Optional[List[str]]) -> bool:
        """Check if file should be excluded."""
        if not patterns:
            return False
        return any(fnmatch(filename, pattern) for pattern in patterns)

    def _should_exclude_tar(self, tarinfo: tarfile.TarInfo) -> Optional[tarfile.TarInfo]:
        """Filter function for tar exclusion."""
        # This is a simplified version - could be enhanced
        return tarinfo


@register_tool(category=ToolCategory.FILE_OPERATION, name="extract_archive",
               description="Extract archives (zip, tar, gzip) with progress tracking")
class ExtractArchiveTool(AsyncTool):
    """Tool for extracting archives."""

    async def execute(self, archive_path: str, destination: str,
                     overwrite: bool = False, preserve_permissions: bool = True) -> ToolResult:
        """Extract an archive.

        Args:
            archive_path: Path to the archive file
            destination: Directory to extract to
            overwrite: Whether to overwrite existing files
            preserve_permissions: Whether to preserve file permissions

        Returns:
            ToolResult: Extraction result
        """
        try:
            archive_file = Path(archive_path)
            dest_dir = Path(destination)

            if not archive_file.exists():
                return ToolResult(success=False, error=f"Archive does not exist: {archive_path}")

            # Determine archive type
            archive_type = ArchiveHelper.detect_archive_type(archive_file)
            if not archive_type:
                return ToolResult(success=False, error=f"Unsupported archive format: {archive_path}")

            # Create destination directory
            dest_dir.mkdir(parents=True, exist_ok=True)

            progress = ProgressIndicator()

            if archive_type == 'zip':
                extracted_files = await self._extract_zip(archive_file, dest_dir, overwrite, progress)
            elif archive_type == 'tar':
                extracted_files = await self._extract_tar(archive_file, dest_dir, overwrite, preserve_permissions, progress)
            else:
                return ToolResult(success=False, error=f"Unsupported archive type: {archive_type}")

            return ToolResult(success=True, data={
                "archive_path": str(archive_file),
                "destination": str(dest_dir),
                "archive_type": archive_type,
                "extracted_files": extracted_files,
                "total_files": len(extracted_files),
                "message": f"Archive extracted successfully to {dest_dir}"
            })

        except Exception as e:
            return ToolResult(success=False, error=f"Archive extraction failed: {str(e)}")

    async def _extract_zip(self, archive_file: Path, dest_dir: Path,
                          overwrite: bool, progress: ProgressIndicator) -> List[str]:
        """Extract ZIP archive."""
        extracted = []
        with zipfile.ZipFile(archive_file, 'r') as zf:
            task_id = progress.start_task("Extracting ZIP", total=len(zf.namelist()))

            for i, member in enumerate(zf.namelist()):
                dest_path = dest_dir / member

                if dest_path.exists() and not overwrite:
                    continue

                dest_path.parent.mkdir(parents=True, exist_ok=True)
                zf.extract(member, str(dest_dir))
                extracted.append(member)

                progress.update_task(task_id, i + 1, len(zf.namelist()), f"Extracting {member}")

            progress.complete_task(task_id)

        return extracted

    async def _extract_tar(self, archive_file: Path, dest_dir: Path,
                          overwrite: bool, preserve_permissions: bool,
                          progress: ProgressIndicator) -> List[str]:
        """Extract TAR archive."""
        extracted = []
        with tarfile.open(archive_file, 'r') as tf:
            task_id = progress.start_task("Extracting TAR", total=len(tf.getmembers()))

            for i, member in enumerate(tf.getmembers()):
                dest_path = dest_dir / member.name

                if dest_path.exists() and not overwrite:
                    continue

                tf.extract(member, str(dest_dir), set_attrs=preserve_permissions)
                extracted.append(member.name)

                progress.update_task(task_id, i + 1, len(tf.getmembers()), f"Extracting {member.name}")

            progress.complete_task(task_id)

        return extracted


@register_tool(category=ToolCategory.FILE_OPERATION, name="compress_file",
               description="Compress individual files with gzip, bzip2, or lzma")
class CompressFileTool(SyncTool):
    """Tool for compressing individual files."""

    def execute_sync(self, source_file: str, compression_type: str = "gzip",
                    compression_level: int = 6, remove_original: bool = False) -> ToolResult:
        """Compress a file.

        Args:
            source_file: Path to file to compress
            compression_type: Compression type (gzip, bzip2, lzma)
            compression_level: Compression level (1-9)
            remove_original: Whether to remove the original file after compression

        Returns:
            ToolResult: Compression result
        """
        try:
            source_path = Path(source_file)
            if not source_path.exists() or not source_path.is_file():
                return ToolResult(success=False, error=f"Source file does not exist: {source_file}")

            # Determine output filename
            if compression_type == "gzip":
                compressed_path = source_path.with_suffix(source_path.suffix + '.gz')
                opener = gzip.open
            elif compression_type == "bzip2":
                compressed_path = source_path.with_suffix(source_path.suffix + '.bz2')
                opener = bz2.open
            elif compression_type == "lzma":
                compressed_path = source_path.with_suffix(source_path.suffix + '.xz')
                opener = lzma.open
            else:
                return ToolResult(success=False, error=f"Unsupported compression type: {compression_type}")

            if compressed_path.exists():
                return ToolResult(success=False, error=f"Compressed file already exists: {compressed_path}")

            # Compress the file
            original_size = source_path.stat().st_size

            with open(source_path, 'rb') as src, \
                 opener(compressed_path, 'wb', compresslevel=compression_level) as dst:
                shutil.copyfileobj(src, dst)

            compressed_size = compressed_path.stat().st_size
            compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

            # Remove original if requested
            if remove_original:
                source_path.unlink()

            return ToolResult(success=True, data={
                "source_file": str(source_path),
                "compressed_file": str(compressed_path),
                "compression_type": compression_type,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": round(compression_ratio, 2),
                "original_removed": remove_original
            })

        except Exception as e:
            return ToolResult(success=False, error=f"File compression failed: {str(e)}")


@register_tool(category=ToolCategory.FILE_OPERATION, name="decompress_file",
               description="Decompress individual compressed files")
class DecompressFileTool(SyncTool):
    """Tool for decompressing individual files."""

    def execute_sync(self, compressed_file: str, output_file: Optional[str] = None,
                    remove_compressed: bool = False) -> ToolResult:
        """Decompress a file.

        Args:
            compressed_file: Path to compressed file
            output_file: Output file path (optional)
            remove_compressed: Whether to remove the compressed file after decompression

        Returns:
            ToolResult: Decompression result
        """
        try:
            compressed_path = Path(compressed_file)
            if not compressed_path.exists() or not compressed_path.is_file():
                return ToolResult(success=False, error=f"Compressed file does not exist: {compressed_file}")

            # Determine compression type and output filename
            compression_type = ArchiveHelper.detect_archive_type(compressed_path)
            if not compression_type:
                return ToolResult(success=False, error=f"Unsupported compression format: {compressed_file}")

            if output_file:
                output_path = Path(output_file)
            else:
                # Remove compression extension
                if compression_type == "gzip":
                    output_path = compressed_path.with_suffix('')
                elif compression_type == "bzip2":
                    output_path = compressed_path.with_suffix('')
                elif compression_type == "lzma":
                    output_path = compressed_path.with_suffix('')
                else:
                    return ToolResult(success=False, error=f"Cannot determine output filename for {compression_type}")

            if output_path.exists():
                return ToolResult(success=False, error=f"Output file already exists: {output_path}")

            # Determine opener
            if compression_type == "gzip":
                opener = gzip.open
            elif compression_type == "bzip2":
                opener = bz2.open
            elif compression_type == "lzma":
                opener = lzma.open
            else:
                return ToolResult(success=False, error=f"Unsupported compression type: {compression_type}")

            # Decompress the file
            compressed_size = compressed_path.stat().st_size

            with opener(compressed_path, 'rb') as src, \
                 open(output_path, 'wb') as dst:
                shutil.copyfileobj(src, dst)

            output_size = output_path.stat().st_size

            # Remove compressed file if requested
            if remove_compressed:
                compressed_path.unlink()

            return ToolResult(success=True, data={
                "compressed_file": str(compressed_path),
                "output_file": str(output_path),
                "compression_type": compression_type,
                "compressed_size": compressed_size,
                "output_size": output_size,
                "compressed_removed": remove_compressed
            })

        except Exception as e:
            return ToolResult(success=False, error=f"File decompression failed: {str(e)}")


@register_tool(category=ToolCategory.FILE_OPERATION, name="list_archive",
               description="List contents of archives without extracting")
class ListArchiveTool(SyncTool):
    """Tool for listing archive contents."""

    def execute_sync(self, archive_path: str) -> ToolResult:
        """List archive contents.

        Args:
            archive_path: Path to archive file

        Returns:
            ToolResult: Archive contents
        """
        try:
            archive_file = Path(archive_path)
            if not archive_file.exists():
                return ToolResult(success=False, error=f"Archive does not exist: {archive_path}")

            archive_type = ArchiveHelper.detect_archive_type(archive_file)
            if not archive_type:
                return ToolResult(success=False, error=f"Unsupported archive format: {archive_path}")

            contents = []

            if archive_type == 'zip':
                with zipfile.ZipFile(archive_file, 'r') as zf:
                    for info in zf.filelist:
                        contents.append({
                            "filename": info.filename,
                            "size": info.file_size,
                            "compressed_size": info.compress_size,
                            "date_time": info.date_time,
                            "is_dir": info.is_dir()
                        })

            elif archive_type == 'tar':
                with tarfile.open(archive_file, 'r') as tf:
                    for member in tf.getmembers():
                        contents.append({
                            "filename": member.name,
                            "size": member.size,
                            "mode": member.mode,
                            "mtime": member.mtime,
                            "is_dir": member.isdir()
                        })

            return ToolResult(success=True, data={
                "archive_path": str(archive_file),
                "archive_type": archive_type,
                "contents": contents,
                "total_files": len(contents)
            })

        except Exception as e:
            return ToolResult(success=False, error=f"Archive listing failed: {str(e)}")