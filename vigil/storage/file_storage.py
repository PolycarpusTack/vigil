"""File-based storage backend."""

import csv
import json
import logging
import os
import stat
import threading
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

from vigil.core.event import AuditEvent
from vigil.core.exceptions import StorageError
from vigil.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class FileStorageBackend(StorageBackend):
    """File-based audit event storage."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize file storage backend.

        Args:
            config: Configuration dictionary with keys:
                - directory: Base directory for log files
                - format: Output format (json, jsonl, csv, text)
                - filename_pattern: Filename pattern (default: {app_name}_audit_{date}.log)
                - rotation: Rotation configuration (optional)
        """
        super().__init__(config)

        # Configuration
        self.directory = Path(config.get("directory", "./logs/audit"))
        self.format = config.get("format", "json").lower()
        self.filename_pattern = config.get("filename_pattern", "audit_{date}.log")

        # Create directory if it doesn't exist
        try:
            self.directory.mkdir(parents=True, exist_ok=True)

            # Set restrictive permissions on directory (owner read/write/execute only)
            # 0o700 = rwx------ (owner only)
            try:
                os.chmod(self.directory, stat.S_IRWXU)
                logger.debug(f"Set secure permissions (0700) on directory: {self.directory}")
            except (OSError, PermissionError) as perm_error:
                # Log warning but don't fail - might be on Windows or restricted environment
                logger.warning(
                    f"Could not set restrictive permissions on {self.directory}: {perm_error}. "
                    "Audit logs may be readable by other users."
                )
        except Exception as e:
            raise StorageError(f"Failed to create audit log directory: {e}")

        # File handle management (for buffered writes and rotation)
        self._current_file: Optional[Any] = None
        self._current_file_path: Optional[Path] = None
        self._current_date: Optional[date] = None
        self._file_lock = threading.Lock()

        logger.info(
            f"FileStorageBackend initialized: " f"directory={self.directory}, format={self.format}"
        )

    def store(self, event: AuditEvent):
        """
        Store audit event to file with file handle caching and rotation.

        Args:
            event: AuditEvent to store
        """
        with self._file_lock:
            try:
                # Get file path
                file_path = self._get_file_path(event)
                current_date = event.timestamp.date()

                # Check if we need to rotate (date changed or file path changed)
                if self._current_date != current_date or self._current_file_path != file_path:
                    self._rotate_file()
                    self._current_date = current_date
                    self._current_file_path = file_path

                # Format event
                if self.format == "json":
                    self._write_json(file_path, event)
                elif self.format == "jsonl":
                    self._write_jsonl(file_path, event)
                elif self.format == "csv":
                    self._write_csv(file_path, event)
                elif self.format == "text":
                    self._write_text(file_path, event)
                else:
                    raise StorageError(f"Unsupported format: {self.format}")

            except Exception as e:
                raise StorageError(f"Failed to store event to file: {e}")

    def _get_file_path(self, event: AuditEvent) -> Path:
        """
        Get file path for event.

        Args:
            event: AuditEvent

        Returns:
            Path to log file
        """
        # Format filename
        date_str = event.timestamp.strftime("%Y-%m-%d")
        category = event.action.category.lower()

        filename = self.filename_pattern.format(
            app_name="audit",
            date=date_str,
            category=category,
        )

        return self.directory / filename

    def _rotate_file(self):
        """Close current file handle to prepare for rotation.

        Called when date changes or file path changes.
        """
        if self._current_file:
            try:
                self._current_file.close()
                logger.debug(f"Rotated file: {self._current_file_path}")
            except Exception as e:
                logger.error(f"Error closing file during rotation: {e}")
            finally:
                self._current_file = None

    def _get_or_open_file(self, file_path: Path, mode: str = "a"):
        """Get cached file handle or open new one.

        Args:
            file_path: Path to file
            mode: File open mode (default: 'a' for append)

        Returns:
            Open file handle
        """
        if self._current_file is None:
            is_new_file = not file_path.exists()

            self._current_file = open(file_path, mode, encoding="utf-8", newline="")
            logger.debug(f"Opened file handle: {file_path}")

            # Set restrictive permissions on new files
            if is_new_file:
                self._set_file_permissions(file_path)

        return self._current_file

    def _set_file_permissions(self, file_path: Path):
        """Set restrictive permissions on audit log file.

        Sets file to owner read/write only (0o600 = rw-------).

        Args:
            file_path: Path to file
        """
        try:
            # 0o600 = rw------- (owner read/write only)
            os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
            logger.debug(f"Set secure permissions (0600) on file: {file_path}")
        except (OSError, PermissionError) as e:
            # Log warning but don't fail - might be on Windows or restricted environment
            logger.warning(
                f"Could not set restrictive permissions on {file_path}: {e}. "
                "Audit log may be readable by other users."
            )

    def _write_json(self, file_path: Path, event: AuditEvent):
        """Write event as JSON (one event per line, human-readable).

        Uses cached file handle for better performance.
        """
        f = self._get_or_open_file(file_path)
        json.dump(event.to_dict(), f, default=str)
        f.write("\n")
        f.flush()  # Ensure data is written to disk

    def _write_jsonl(self, file_path: Path, event: AuditEvent):
        """Write event as JSONL (compact, one event per line).

        Uses cached file handle for better performance.
        """
        f = self._get_or_open_file(file_path)
        f.write(event.to_json())
        f.write("\n")
        f.flush()  # Ensure data is written to disk

    def _write_csv(self, file_path: Path, event: AuditEvent):
        """Write event as CSV.

        Uses cached file handle and handles header writing correctly.
        """
        # Flatten event to single-level dict
        flat_event = self._flatten_event(event)

        # Check if file exists and has content
        file_exists = file_path.exists() and file_path.stat().st_size > 0

        # Get or open file
        f = self._get_or_open_file(file_path)

        # Create CSV writer
        writer = csv.DictWriter(f, fieldnames=flat_event.keys())

        # Write header if new file (only once per file)
        if not file_exists and f.tell() == 0:
            writer.writeheader()

        writer.writerow(flat_event)
        f.flush()  # Ensure data is written to disk

    def _write_text(self, file_path: Path, event: AuditEvent):
        """Write event as human-readable text.

        Uses cached file handle for better performance.
        """
        f = self._get_or_open_file(file_path)

        f.write(f"\n{'='*80}\n")
        f.write(f"Event ID: {event.event_id}\n")
        f.write(f"Timestamp: {event.timestamp.isoformat()}\n")
        f.write(f"Category: {event.action.category}\n")
        f.write(f"Action: {event.action.operation}\n")
        f.write(f"Type: {event.action.type}\n")

        if event.actor.username:
            f.write(f"User: {event.actor.username}\n")

        if event.action.parameters:
            f.write(f"Parameters: {json.dumps(event.action.parameters, default=str)}\n")

        if event.performance.duration_ms:
            f.write(f"Duration: {event.performance.duration_ms:.2f}ms\n")

        f.write(f"Status: {event.action.result.status}\n")

        if event.error.occurred:
            f.write(f"\nERROR: {event.error.type}: {event.error.message}\n")
            if event.error.stack_trace:
                f.write(f"Stack Trace:\n{event.error.stack_trace}\n")

        f.write(f"{'='*80}\n")
        f.flush()  # Ensure data is written to disk

    def _flatten_event(self, event: AuditEvent) -> Dict[str, Any]:
        """
        Flatten nested event structure for CSV.

        Args:
            event: AuditEvent

        Returns:
            Flattened dictionary
        """
        return {
            "event_id": event.event_id,
            "timestamp": event.timestamp.isoformat(),
            "category": event.action.category,
            "action_type": event.action.type,
            "operation": event.action.operation,
            "username": event.actor.username,
            "ip_address": event.actor.ip_address,
            "duration_ms": event.performance.duration_ms,
            "status": event.action.result.status,
            "error_occurred": event.error.occurred,
            "error_type": event.error.type if event.error.occurred else None,
            "error_message": event.error.message if event.error.occurred else None,
        }

    def close(self):
        """Close any open file handles."""
        with self._file_lock:
            if self._current_file:
                try:
                    self._current_file.close()
                    logger.info(f"Closed file handle: {self._current_file_path}")
                except Exception as e:
                    logger.error(f"Error closing file: {e}")
                finally:
                    self._current_file = None
                    self._current_file_path = None
                    self._current_date = None

    def __del__(self):
        """Destructor to ensure file handles are closed."""
        try:
            self.close()
        except Exception:
            pass  # Ignore errors during cleanup

    def __repr__(self) -> str:
        """String representation."""
        return f"FileStorageBackend(directory={self.directory}, format={self.format})"
