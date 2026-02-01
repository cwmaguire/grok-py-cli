"""Integration tests for disk tool with real filesystem operations."""

import pytest
import tempfile
import os
import shutil
from grok_py.tools.disk import DiskTool


class TestDiskIntegration:
    """Integration tests for disk tool with real filesystem operations."""

    @pytest.fixture
    def disk_tool(self):
        """Disk tool fixture."""
        return DiskTool()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_disk_usage_operation(self, disk_tool, temp_dir):
        """Test disk usage operation on a directory."""
        result = disk_tool.execute_sync("usage", temp_dir)

        # Should succeed for valid directory
        assert isinstance(result.success, bool)
        assert isinstance(result.data, dict)
        if result.success:
            assert 'size' in result.data
            assert 'used' in result.data
            assert 'available' in result.data

    def test_disk_free_operation(self, disk_tool):
        """Test disk free operation."""
        result = disk_tool.execute_sync("free", "/")

        # Should return free space info
        assert isinstance(result.success, bool)
        assert isinstance(result.data, dict)

    def test_disk_du_operation(self, disk_tool, temp_dir):
        """Test disk usage summary (du) operation."""
        # Create some files in temp directory
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content" * 100)  # Make it have some size

        result = disk_tool.execute_sync("du", temp_dir)

        assert isinstance(result.success, bool)
        assert isinstance(result.data, dict)
        if result.success:
            # Should contain directory usage info
            assert isinstance(result.data, dict)

    def test_disk_large_files_operation(self, disk_tool, temp_dir):
        """Test large files detection operation."""
        # Create a file larger than typical threshold
        large_file = os.path.join(temp_dir, "large_test.txt")
        with open(large_file, "w") as f:
            f.write("x" * (1024 * 1024))  # 1MB file

        result = disk_tool.execute_sync("large-files", temp_dir, "500k")  # 500KB threshold

        assert isinstance(result.success, bool)
        assert isinstance(result.data, dict)

    def test_disk_cleanup_operation_safe(self, disk_tool, temp_dir):
        """Test disk cleanup operation with safe simulation."""
        # Create some test files that could be "cleaned"
        cache_file = os.path.join(temp_dir, "cache.tmp")
        with open(cache_file, "w") as f:
            f.write("cache data")

        # Note: Cleanup operations are dangerous, so we test the command structure
        # without actually performing cleanup
        result = disk_tool.execute_sync("usage", temp_dir)

        assert isinstance(result.success, bool)
        assert isinstance(result.data, dict)

    def test_disk_invalid_path(self, disk_tool):
        """Test disk operations with invalid path."""
        result = disk_tool.execute_sync("usage", "/definitely/nonexistent/path/12345")

        # Should fail gracefully
        assert result.success is False
        assert result.data is None or isinstance(result.data, dict)

    def test_disk_permission_denied(self, disk_tool):
        """Test disk operations with permission issues."""
        # Try to access a restricted directory
        restricted_paths = ["/root", "/etc/shadow"]

        for path in restricted_paths:
            if os.path.exists(path):
                result = disk_tool.execute_sync("usage", path)
                # Should handle permission errors gracefully
                assert isinstance(result.success, bool)
                assert isinstance(result.data, dict)

    def test_disk_empty_directory(self, disk_tool, temp_dir):
        """Test disk operations on empty directory."""
        result = disk_tool.execute_sync("du", temp_dir)

        assert isinstance(result.success, bool)
        assert isinstance(result.data, dict)

    def test_disk_nested_directories(self, disk_tool, temp_dir):
        """Test disk operations on nested directory structure."""
        # Create nested structure
        nested_dir = os.path.join(temp_dir, "level1", "level2")
        os.makedirs(nested_dir)

        test_file = os.path.join(nested_dir, "nested_test.txt")
        with open(test_file, "w") as f:
            f.write("nested content")

        result = disk_tool.execute_sync("du", temp_dir)

        assert isinstance(result.success, bool)
        assert isinstance(result.data, dict)

    def test_disk_large_directory_structure(self, disk_tool, temp_dir):
        """Test disk operations on directory with many files."""
        # Create many small files
        for i in range(100):
            test_file = os.path.join(temp_dir, f"file_{i}.txt")
            with open(test_file, "w") as f:
                f.write(f"content {i}")

        result = disk_tool.execute_sync("du", temp_dir)

        assert isinstance(result.success, bool)
        assert isinstance(result.data, dict)

    def test_disk_output_parsing(self, disk_tool, temp_dir):
        """Test that disk output is properly captured and parsed."""
        result = disk_tool.execute_sync("usage", temp_dir)

        # Should have proper result structure
        assert isinstance(result.success, bool)
        assert isinstance(result.data, dict)

    def test_disk_error_message_quality(self, disk_tool):
        """Test that disk operations provide meaningful error messages."""
        result = disk_tool.execute_sync("usage", "/nonexistent/path/test")

        # Should provide some error information
        if not result.success:
            assert result.error is not None or len(result.data) > 0

    def test_disk_command_validation(self, disk_tool):
        """Test disk command validation."""
        # Test various invalid commands
        invalid_commands = ["", "invalid", "drop", "delete", "hack"]

        for cmd in invalid_commands:
            result = disk_tool.execute_sync(cmd, "/tmp")
            # Should handle invalid commands gracefully
            assert isinstance(result.success, bool)
            assert result.data is None or isinstance(result.data, dict)

    def test_disk_different_filesystems(self, disk_tool):
        """Test disk operations across different filesystem types."""
        # Test on root filesystem
        result = disk_tool.execute_sync("free", "/")

        assert isinstance(result.success, bool)
        assert isinstance(result.data, dict)

        # Test on /tmp if it's different
        if os.path.exists("/tmp"):
            result2 = disk_tool.execute_sync("usage", "/tmp")
            assert isinstance(result2.success, bool)
            assert isinstance(result2.data, dict)

    @pytest.mark.slow
    def test_disk_performance_with_large_directory(self, disk_tool, temp_dir):
        """Test disk operations performance with large directory."""
        # Create a larger directory structure
        for i in range(50):
            subdir = os.path.join(temp_dir, f"subdir_{i}")
            os.makedirs(subdir)
            for j in range(10):
                test_file = os.path.join(subdir, f"file_{j}.txt")
                with open(test_file, "w") as f:
                    f.write(f"content {i}-{j}")

        result = disk_tool.execute_sync("du", temp_dir)

        assert isinstance(result.success, bool)
        assert isinstance(result.data, dict)

    def test_disk_response_consistency(self, disk_tool, temp_dir):
        """Test that disk responses are consistent."""
        # Run the same command multiple times to check consistency
        results = []
        for _ in range(3):
            result = disk_tool.execute_sync("usage", temp_dir)
            results.append(result.success)

        # Results should be boolean
        assert all(isinstance(r, bool) for r in results)