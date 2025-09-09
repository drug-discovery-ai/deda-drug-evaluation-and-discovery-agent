"""Unified Snapshot Testing System for API responses.

This package provides HTTP-level interception to transparently capture and replay
API responses, enabling fast and reliable testing of external API integrations.

The unified system provides command-line interface with snapshots as the default:

Usage:
    # Default behavior - uses existing snapshots (fast, no network calls)
    pytest

    # Record new snapshots from live API calls
    pytest --update-snapshots

    # Validate existing snapshots against live APIs
    pytest --validate-snapshots

Features:
    - HTTP-level interception (transparent to application code)
    - Conditional interception (unit vs integration tests)
    - Multiple backends (snapshot, recording, validation)
    - Proper HTTP error handling and status codes
"""

from .http_interceptor import (
    HTTPBackend,
    HTTPInterceptor,
    SnapshotHTTPBackend,
    SnapshotRecordingBackend,
    SnapshotValidationBackend,
)
from .manager import SnapshotManager

__version__ = "2.0.0"
__all__ = [
    # Unified System (Phase 2)
    "HTTPInterceptor",
    "HTTPBackend",
    "SnapshotHTTPBackend",
    "SnapshotRecordingBackend",
    "SnapshotValidationBackend",
    "SnapshotManager",
]
