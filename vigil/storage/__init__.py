"""Storage backend implementations."""

from vigil.storage.base import StorageBackend
from vigil.storage.file_storage import FileStorageBackend

__all__ = ["StorageBackend", "FileStorageBackend"]


# Lazy imports for optional backends
def get_sql_storage_backend():
    """Get SQLStorageBackend class (requires sqlalchemy)."""
    from vigil.storage.sql_storage import SQLStorageBackend

    return SQLStorageBackend
