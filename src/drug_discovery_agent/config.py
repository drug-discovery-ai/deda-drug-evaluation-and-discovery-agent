"""
Configuration constants for the Drug Discovery Agent application.

This module provides centralized configuration for host and port settings
used across both the MCP server and Chat server components.
"""

import os

DEFAULT_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("SERVER_PORT", "8080"))

BACKEND_HOST = DEFAULT_HOST
BACKEND_PORT = DEFAULT_PORT
