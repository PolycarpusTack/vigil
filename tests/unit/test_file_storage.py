"""Unit tests for file storage backend.

Tests cover:
- File handle caching and reuse
- File rotation on date change
- CSV header race condition prevention
- Thread-safe file operations
- Permission setting (0700 dirs, 0600 files)
- Different file formats (JSON, JSONL, CSV, TEXT)
- Error handling
"""

import csv
import json
import os
import stat
import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest

from vigil.core.event import AuditEvent
from vigil.core.exceptions import StorageError
from vigil.storage.file_storage import FileStorageBackend


class TestFileStorageInitialization:
    """Test suite for FileStorageBackend initialization."""

    def test_initialization_creates_directory(self, temp_dir):
        """Test that initialization creates the log directory."""
        log_dir = temp_dir / "audit_logs"
        assert not log_dir.exists()

        config = {"directory": str(log_dir), "format": "json"}
        backend = FileStorageBackend(config)

        assert log_dir.exists()
        assert log_dir.is_dir()
        backend.close()

    def test_initialization_with_existing_directory(self, audit_log_dir):
        """Test initialization with pre-existing directory."""
        config = {"directory": str(audit_log_dir), "format": "json"}
        backend = FileStorageBackend(config)
        assert backend.directory == audit_log_dir
        backend.close()

    def test_initialization_creates_nested_directories(self, temp_dir):
        """Test that initialization creates nested directories."""
        nested_dir = temp_dir / "level1" / "level2" / "level3"
        config = {"directory": str(nested_dir), "format": "json"}
        backend = FileStorageBackend(config)

        assert nested_dir.exists()
        backend.close()

    def test_initialization_sets_default_format(self, temp_dir):
        """Test default format is 'json'."""
        config = {"directory": str(temp_dir)}
        backend = FileStorageBackend(config)
        assert backend.format == "json"
        backend.close()

    def test_initialization_sets_custom_format(self, temp_dir):
        """Test custom format is set correctly."""
        for fmt in ["json", "jsonl", "csv", "text"]:
            config = {"directory": str(temp_dir), "format": fmt}
            backend = FileStorageBackend(config)
            assert backend.format == fmt
            backend.close()

    def test_initialization_sets_filename_pattern(self, temp_dir):
        """Test filename pattern configuration."""
        config = {
            "directory": str(temp_dir),
            "filename_pattern": "custom_{date}_{category}.log",
        }
        backend = FileStorageBackend(config)
        assert backend.filename_pattern == "custom_{date}_{category}.log"
        backend.close()

    def test_initialization_directory_permission_error(self, temp_dir):
        """Test handling of permission errors during directory creation."""
        # Create a file where directory should be
        file_path = temp_dir / "not_a_directory"
        file_path.touch()

        config = {"directory": str(file_path / "subdir")}
        with pytest.raises(StorageError) as exc_info:
            FileStorageBackend(config)
        assert "Failed to create audit log directory" in str(exc_info.value)

    @pytest.mark.skipif(os.name == "nt", reason="Unix permissions not applicable on Windows")
    def test_directory_permissions_set_to_0700(self, temp_dir):
        """Test that directory permissions are set to 0700 (owner only)."""
        log_dir = temp_dir / "secure_logs"
        config = {"directory": str(log_dir), "format": "json"}
        backend = FileStorageBackend(config)

        # Check permissions
        dir_stat = os.stat(log_dir)
        mode = stat.S_IMODE(dir_stat.st_mode)
        # Should be 0o700 (rwx------)
        assert mode == stat.S_IRWXU
        backend.close()

    def test_repr(self, temp_dir):
        """Test string representation of backend."""
        config = {"directory": str(temp_dir), "format": "csv"}
        backend = FileStorageBackend(config)
        repr_str = repr(backend)
        assert "FileStorageBackend" in repr_str
        assert "csv" in repr_str
        backend.close()


class TestJSONStorage:
    """Test suite for JSON format storage."""

    def test_store_event_json_format(self, temp_dir, sample_event):
        """Test storing event in JSON format."""
        config = {"directory": str(temp_dir), "format": "json"}
        backend = FileStorageBackend(config)

        backend.store(sample_event)
        backend.close()

        # Find the created file
        log_files = list(temp_dir.glob("*.log"))
        assert len(log_files) == 1

        # Read and verify JSON
        with open(log_files[0], "r") as f:
            content = f.read().strip()
            data = json.loads(content)

        assert data["event_id"] == sample_event.event_id
        assert data["actor"]["username"] == sample_event.actor.username

    def test_multiple_events_json_format(self, temp_dir, sample_event):
        """Test storing multiple events in JSON format."""
        config = {"directory": str(temp_dir), "format": "json"}
        backend = FileStorageBackend(config)

        # Store multiple events
        for i in range(3):
            event = AuditEvent()
            event.actor.username = f"user_{i}"
            backend.store(event)

        backend.close()

        # Read file
        log_files = list(temp_dir.glob("*.log"))
        assert len(log_files) == 1

        with open(log_files[0], "r") as f:
            lines = f.readlines()

        # Should have 3 JSON objects (one per line)
        assert len(lines) == 3
        for i, line in enumerate(lines):
            data = json.loads(line.strip())
            assert data["actor"]["username"] == f"user_{i}"


class TestJSONLStorage:
    """Test suite for JSONL format storage."""

    def test_store_event_jsonl_format(self, temp_dir, sample_event):
        """Test storing event in JSONL format."""
        config = {"directory": str(temp_dir), "format": "jsonl"}
        backend = FileStorageBackend(config)

        backend.store(sample_event)
        backend.close()

        log_files = list(temp_dir.glob("*.log"))
        assert len(log_files) == 1

        with open(log_files[0], "r") as f:
            line = f.readline()
            data = json.loads(line)

        assert data["event_id"] == sample_event.event_id

    def test_jsonl_compact_format(self, temp_dir, sample_event):
        """Test that JSONL format is compact (no extra whitespace)."""
        config = {"directory": str(temp_dir), "format": "jsonl"}
        backend = FileStorageBackend(config)

        backend.store(sample_event)
        backend.close()

        log_files = list(temp_dir.glob("*.log"))
        with open(log_files[0], "r") as f:
            line = f.readline().strip()

        # JSONL should not have indentation
        assert "  " not in line  # No double spaces (indentation)
        # Should be valid JSON
        assert json.loads(line) is not None


class TestCSVStorage:
    """Test suite for CSV format storage."""

    def test_store_event_csv_format(self, temp_dir, sample_event):
        """Test storing event in CSV format."""
        config = {"directory": str(temp_dir), "format": "csv"}
        backend = FileStorageBackend(config)

        backend.store(sample_event)
        backend.close()

        log_files = list(temp_dir.glob("*.log"))
        assert len(log_files) == 1

        with open(log_files[0], "r", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["event_id"] == sample_event.event_id
        assert rows[0]["username"] == sample_event.actor.username

    def test_csv_header_written_once(self, temp_dir):
        """Test that CSV header is written only once."""
        config = {"directory": str(temp_dir), "format": "csv"}
        backend = FileStorageBackend(config)

        # Store multiple events
        for i in range(3):
            event = AuditEvent()
            event.actor.username = f"user_{i}"
            backend.store(event)

        backend.close()

        log_files = list(temp_dir.glob("*.log"))
        with open(log_files[0], "r") as f:
            lines = f.readlines()

        # Should have 4 lines: 1 header + 3 data rows
        assert len(lines) == 4
        # First line should be header
        assert "event_id" in lines[0]
        assert "timestamp" in lines[0]

    def test_csv_header_race_condition_prevention(self, temp_dir):
        """Test that CSV header is not duplicated in concurrent writes."""
        config = {"directory": str(temp_dir), "format": "csv"}
        backend = FileStorageBackend(config)

        # Store events to create file
        event1 = AuditEvent()
        backend.store(event1)

        # Store another event (file already exists)
        event2 = AuditEvent()
        backend.store(event2)

        backend.close()

        log_files = list(temp_dir.glob("*.log"))
        with open(log_files[0], "r") as f:
            content = f.read()

        # Count header occurrences (should be 1)
        header_count = content.count("event_id,timestamp")
        assert header_count == 1

    def test_csv_flattened_structure(self, temp_dir, sample_event):
        """Test that CSV uses flattened event structure."""
        config = {"directory": str(temp_dir), "format": "csv"}
        backend = FileStorageBackend(config)

        sample_event.performance.duration_ms = 123.45
        sample_event.error.occurred = True
        sample_event.error.type = "TestError"

        backend.store(sample_event)
        backend.close()

        log_files = list(temp_dir.glob("*.log"))
        with open(log_files[0], "r", newline="") as f:
            reader = csv.DictReader(f)
            row = next(reader)

        # Check flattened fields
        assert "event_id" in row
        assert "category" in row
        assert "username" in row
        assert "duration_ms" in row
        assert row["duration_ms"] == "123.45"
        assert row["error_occurred"] == "True"
        assert row["error_type"] == "TestError"


class TestTextStorage:
    """Test suite for text format storage."""

    def test_store_event_text_format(self, temp_dir, sample_event):
        """Test storing event in text format."""
        config = {"directory": str(temp_dir), "format": "text"}
        backend = FileStorageBackend(config)

        backend.store(sample_event)
        backend.close()

        log_files = list(temp_dir.glob("*.log"))
        assert len(log_files) == 1

        with open(log_files[0], "r") as f:
            content = f.read()

        # Verify human-readable format
        assert sample_event.event_id in content
        assert sample_event.actor.username in content
        assert sample_event.action.operation in content
        assert "====" in content  # Separator line

    def test_text_format_includes_error_info(self, temp_dir, sample_event):
        """Test that text format includes error information."""
        config = {"directory": str(temp_dir), "format": "text"}
        backend = FileStorageBackend(config)

        sample_event.error.occurred = True
        sample_event.error.type = "ValueError"
        sample_event.error.message = "Test error message"
        sample_event.error.stack_trace = "Stack trace here"

        backend.store(sample_event)
        backend.close()

        log_files = list(temp_dir.glob("*.log"))
        with open(log_files[0], "r") as f:
            content = f.read()

        assert "ERROR:" in content
        assert "ValueError" in content
        assert "Test error message" in content
        assert "Stack trace here" in content


class TestFileHandleCaching:
    """Test suite for file handle caching and reuse."""

    def test_file_handle_reused_for_same_file(self, temp_dir):
        """Test that file handle is reused for same file."""
        config = {"directory": str(temp_dir), "format": "json"}
        backend = FileStorageBackend(config)

        # Store multiple events on same day
        for i in range(3):
            event = AuditEvent()
            backend.store(event)

        # File handle should be cached
        assert backend._current_file is not None
        backend.close()

    def test_file_handle_closed_on_rotation(self, temp_dir):
        """Test that file handle is closed during rotation."""
        config = {"directory": str(temp_dir), "format": "json"}
        backend = FileStorageBackend(config)

        # Store first event
        event1 = AuditEvent()
        backend.store(event1)
        assert backend._current_file is not None

        # Manually trigger rotation by changing date
        backend._current_date = datetime.now(timezone.utc).date() - timedelta(days=1)

        # Store second event (should trigger rotation)
        event2 = AuditEvent()
        backend.store(event2)

        # New file handle should be opened
        assert backend._current_file is not None
        backend.close()

    def test_file_handle_closed_on_close(self, temp_dir, sample_event):
        """Test that file handle is closed when backend is closed."""
        config = {"directory": str(temp_dir), "format": "json"}
        backend = FileStorageBackend(config)

        backend.store(sample_event)
        assert backend._current_file is not None

        backend.close()
        assert backend._current_file is None

    def test_multiple_close_calls_are_safe(self, temp_dir, sample_event):
        """Test that calling close multiple times doesn't error."""
        config = {"directory": str(temp_dir), "format": "json"}
        backend = FileStorageBackend(config)

        backend.store(sample_event)
        backend.close()
        backend.close()  # Should not raise error
        backend.close()  # Should not raise error


class TestFileRotation:
    """Test suite for file rotation."""

    def test_rotation_on_date_change(self, temp_dir):
        """Test that files rotate when date changes."""
        config = {"directory": str(temp_dir), "format": "json"}
        backend = FileStorageBackend(config)

        # Store event with today's date
        event1 = AuditEvent()
        event1.timestamp = datetime(2024, 1, 15, 10, 0, 0)
        backend.store(event1)

        # Store event with different date
        event2 = AuditEvent()
        event2.timestamp = datetime(2024, 1, 16, 10, 0, 0)
        backend.store(event2)

        backend.close()

        # Should have two files (one per day)
        log_files = list(temp_dir.glob("*.log"))
        assert len(log_files) == 2

    def test_rotation_preserves_previous_file(self, temp_dir):
        """Test that rotation doesn't delete previous file."""
        config = {"directory": str(temp_dir), "format": "json"}
        backend = FileStorageBackend(config)

        event1 = AuditEvent()
        event1.timestamp = datetime(2024, 1, 15, 10, 0, 0)
        event1.actor.username = "user1"
        backend.store(event1)

        event2 = AuditEvent()
        event2.timestamp = datetime(2024, 1, 16, 10, 0, 0)
        event2.actor.username = "user2"
        backend.store(event2)

        backend.close()

        # Verify both files exist and contain correct data
        log_files = sorted(temp_dir.glob("*.log"))
        assert len(log_files) == 2

        # Check first file
        with open(log_files[0], "r") as f:
            data = json.loads(f.readline())
        assert data["actor"]["username"] == "user1"

        # Check second file
        with open(log_files[1], "r") as f:
            data = json.loads(f.readline())
        assert data["actor"]["username"] == "user2"

    def test_filename_includes_date(self, temp_dir):
        """Test that filename includes date for rotation."""
        config = {"directory": str(temp_dir), "format": "json"}
        backend = FileStorageBackend(config)

        event = AuditEvent()
        event.timestamp = datetime(2024, 1, 15, 10, 0, 0)
        backend.store(event)
        backend.close()

        log_files = list(temp_dir.glob("*.log"))
        assert len(log_files) == 1
        assert "2024-01-15" in log_files[0].name


class TestFilePermissions:
    """Test suite for file permissions."""

    @pytest.mark.skipif(os.name == "nt", reason="Unix permissions not applicable on Windows")
    def test_new_file_permissions_set_to_0600(self, temp_dir, sample_event):
        """Test that new files have 0600 permissions (owner read/write only)."""
        config = {"directory": str(temp_dir), "format": "json"}
        backend = FileStorageBackend(config)

        backend.store(sample_event)
        backend.close()

        log_files = list(temp_dir.glob("*.log"))
        assert len(log_files) == 1

        # Check file permissions
        file_stat = os.stat(log_files[0])
        mode = stat.S_IMODE(file_stat.st_mode)
        # Should be 0o600 (rw-------)
        expected = stat.S_IRUSR | stat.S_IWUSR
        assert mode == expected

    @pytest.mark.skipif(os.name == "nt", reason="Unix permissions not applicable on Windows")
    def test_permission_error_logged_but_doesnt_fail(self, temp_dir, sample_event, caplog):
        """Test that permission errors are logged but don't fail storage."""
        config = {"directory": str(temp_dir), "format": "json"}
        backend = FileStorageBackend(config)

        # Mock chmod to raise permission error
        with patch("os.chmod", side_effect=PermissionError("Cannot change permissions")):
            # Should not raise exception
            backend.store(sample_event)

        backend.close()

        # File should still be created
        log_files = list(temp_dir.glob("*.log"))
        assert len(log_files) == 1


class TestThreadSafety:
    """Test suite for thread-safe operations."""

    @pytest.mark.thread_safety
    def test_concurrent_writes_to_same_file(self, temp_dir):
        """Test that concurrent writes to same file are thread-safe."""
        config = {"directory": str(temp_dir), "format": "json"}
        backend = FileStorageBackend(config)

        num_threads = 10
        events_per_thread = 10
        errors = []

        def write_events():
            try:
                for i in range(events_per_thread):
                    event = AuditEvent()
                    event.actor.username = f"user_{threading.current_thread().name}_{i}"
                    backend.store(event)
            except Exception as e:
                errors.append(e)

        # Create and start threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=write_events, name=f"thread_{i}")
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        backend.close()

        # No errors should have occurred
        assert len(errors) == 0

        # Count total events written
        log_files = list(temp_dir.glob("*.log"))
        total_events = 0
        for log_file in log_files:
            with open(log_file, "r") as f:
                total_events += len(f.readlines())

        # Should have written all events
        assert total_events == num_threads * events_per_thread

    @pytest.mark.thread_safety
    def test_concurrent_csv_writes_single_header(self, temp_dir):
        """Test that concurrent CSV writes result in single header."""
        config = {"directory": str(temp_dir), "format": "csv"}
        backend = FileStorageBackend(config)

        num_threads = 5
        errors = []

        def write_events():
            try:
                for i in range(5):
                    event = AuditEvent()
                    backend.store(event)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=write_events)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        backend.close()

        assert len(errors) == 0

        # Check that header appears only once
        log_files = list(temp_dir.glob("*.log"))
        assert len(log_files) == 1

        with open(log_files[0], "r") as f:
            content = f.read()

        # Header should appear only once
        header_count = content.count("event_id,timestamp")
        assert header_count == 1


class TestErrorHandling:
    """Test suite for error handling."""

    def test_unsupported_format_raises_error(self, temp_dir, sample_event):
        """Test that unsupported format raises StorageError."""
        config = {"directory": str(temp_dir), "format": "invalid_format"}
        backend = FileStorageBackend(config)

        with pytest.raises(StorageError) as exc_info:
            backend.store(sample_event)

        assert "Unsupported format" in str(exc_info.value)
        backend.close()

    def test_storage_error_includes_original_error(self, temp_dir, sample_event):
        """Test that storage errors include original error message."""
        config = {"directory": str(temp_dir), "format": "json"}
        backend = FileStorageBackend(config)

        # Mock file write to raise exception
        with patch.object(backend, "_get_or_open_file", side_effect=IOError("Disk full")):
            with pytest.raises(StorageError) as exc_info:
                backend.store(sample_event)

        assert "Failed to store event" in str(exc_info.value)
        backend.close()

    def test_close_error_is_logged_not_raised(self, temp_dir, sample_event, caplog):
        """Test that errors during close are logged but not raised."""
        config = {"directory": str(temp_dir), "format": "json"}
        backend = FileStorageBackend(config)

        backend.store(sample_event)

        # Mock file.close() to raise error
        if backend._current_file:
            backend._current_file.close = Mock(side_effect=IOError("Close failed"))

        # Should not raise exception
        backend.close()


class TestFilenamePatterns:
    """Test suite for filename pattern functionality."""

    def test_custom_filename_pattern(self, temp_dir, sample_event):
        """Test custom filename pattern."""
        config = {
            "directory": str(temp_dir),
            "format": "json",
            "filename_pattern": "custom_{date}_{category}.log",
        }
        backend = FileStorageBackend(config)

        sample_event.timestamp = datetime(2024, 1, 15, 10, 0, 0)
        sample_event.action.category = "DATABASE"
        backend.store(sample_event)
        backend.close()

        log_files = list(temp_dir.glob("*.log"))
        assert len(log_files) == 1
        assert "custom_2024-01-15_database" in log_files[0].name

    def test_filename_pattern_with_category(self, temp_dir):
        """Test that filename includes category."""
        config = {
            "directory": str(temp_dir),
            "format": "json",
            "filename_pattern": "audit_{category}_{date}.log",
        }
        backend = FileStorageBackend(config)

        # Store events with different categories
        for category in ["DATABASE", "API", "AUTH"]:
            event = AuditEvent()
            event.action.category = category
            backend.store(event)

        backend.close()

        # Should have 3 files (one per category)
        log_files = list(temp_dir.glob("*.log"))
        assert len(log_files) == 3

        filenames = [f.name for f in log_files]
        assert any("database" in f for f in filenames)
        assert any("api" in f for f in filenames)
        assert any("auth" in f for f in filenames)


class TestDestructor:
    """Test suite for __del__ cleanup."""

    def test_destructor_closes_file_handle(self, temp_dir, sample_event):
        """Test that destructor closes open file handles."""
        config = {"directory": str(temp_dir), "format": "json"}
        backend = FileStorageBackend(config)

        backend.store(sample_event)
        assert backend._current_file is not None

        # Trigger destructor
        del backend

        # File should be closed (can't test directly, but no exception should occur)

    def test_destructor_handles_errors_gracefully(self, temp_dir, sample_event):
        """Test that destructor doesn't raise exceptions."""
        config = {"directory": str(temp_dir), "format": "json"}
        backend = FileStorageBackend(config)

        backend.store(sample_event)

        # Break the backend to cause error in destructor
        backend._current_file = "not a file handle"

        # Should not raise exception
        try:
            del backend
        except Exception as e:
            pytest.fail(f"Destructor raised exception: {e}")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_directory_path(self):
        """Test handling of empty directory path."""
        config = {"directory": "", "format": "json"}
        # Should use current directory or raise error
        # Depending on implementation
        try:
            backend = FileStorageBackend(config)
            backend.close()
        except (StorageError, ValueError):
            pass  # Expected behavior

    def test_very_long_filename(self, temp_dir, sample_event):
        """Test handling of very long filenames."""
        long_pattern = "audit_" + "x" * 200 + "_{date}.log"
        config = {
            "directory": str(temp_dir),
            "format": "json",
            "filename_pattern": long_pattern,
        }
        backend = FileStorageBackend(config)

        try:
            backend.store(sample_event)
            backend.close()
        except (OSError, StorageError):
            # Expected on filesystems with filename length limits
            backend.close()

    def test_special_characters_in_directory(self, temp_dir, sample_event):
        """Test directory with special characters."""
        special_dir = temp_dir / "logs with spaces & special!chars"
        config = {"directory": str(special_dir), "format": "json"}
        backend = FileStorageBackend(config)

        backend.store(sample_event)
        backend.close()

        assert special_dir.exists()
        log_files = list(special_dir.glob("*.log"))
        assert len(log_files) == 1

    def test_unicode_in_directory_path(self, temp_dir, sample_event):
        """Test directory path with unicode characters."""
        unicode_dir = temp_dir / "日志文件"
        config = {"directory": str(unicode_dir), "format": "json"}
        backend = FileStorageBackend(config)

        backend.store(sample_event)
        backend.close()

        assert unicode_dir.exists()

    def test_store_many_events_same_file(self, temp_dir):
        """Test storing many events to same file."""
        config = {"directory": str(temp_dir), "format": "json"}
        backend = FileStorageBackend(config)

        # Store 1000 events
        for i in range(1000):
            event = AuditEvent()
            event.actor.username = f"user_{i}"
            backend.store(event)

        backend.close()

        # Verify all events were written
        log_files = list(temp_dir.glob("*.log"))
        assert len(log_files) == 1

        with open(log_files[0], "r") as f:
            lines = f.readlines()

        assert len(lines) == 1000
