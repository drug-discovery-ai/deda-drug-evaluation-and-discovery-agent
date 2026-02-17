"""API Key storage and retrieval service with multiple backend support."""

import logging
import os
import platform
from enum import Enum
from pathlib import Path
from typing import Any

import keyring
from keyring.errors import KeyringError

from .storage_fallback import EncryptedFileStorage
from .validation import APIKeyValidator


class StorageMethod(Enum):
    """Available storage methods in priority order."""
    ENVIRONMENT = "environment"
    ENCRYPTED_FILE = "encrypted_file"
    NOT_FOUND = "not_found"


class APIKeyManager:
    """Manages API key storage and retrieval with multiple backend support.

    Priority order: environment variables → encrypted file → user prompt
    """

    SERVICE_NAME = "drug-discovery-agent"
    ACCOUNT_NAME = "api_key-key"
    ENV_VAR_API_KEY = "OPENAI_API_KEY"

    def __init__(self, app_name: str = "drug-discovery-agent"):
        self.app_name = app_name
        self.logger = logging.getLogger(__name__)
        self.validator = APIKeyValidator()
        self._encrypted_storage: EncryptedFileStorage | None = None

    @property
    def encrypted_storage(self) -> EncryptedFileStorage:
        """Lazy initialization of encrypted storage."""
        if self._encrypted_storage is None:
            self._encrypted_storage = EncryptedFileStorage(self._get_user_data_dir())
        return self._encrypted_storage

    def _get_user_data_dir(self) -> Path:
        """Get platform-appropriate user data directory.

        Can be overridden with DRUG_DISCOVERY_AGENT_DATA_DIR environment variable.
        """
        # Allow override via environment variable (useful for testing)
        env_override = os.environ.get("DRUG_DISCOVERY_AGENT_DATA_DIR")
        if env_override:
            return Path(env_override)

        system = platform.system()

        if system == "Darwin":  # macOS
            base_dir = Path.home() / "Library" / "Application Support"
        elif system == "Windows":
            base_dir = Path(
                os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
            )
        else:  # Linux and others
            base_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

        return base_dir / self.app_name

    def get_api_key(self) -> tuple[str | None, StorageMethod]:
        """Retrieve API key using priority order: env → encrypted_file.

        Returns:
            Tuple of (api_key, storage_method) where api_key is None if not found.
        """
        # 1. Check environment variables first (highest priority)
        env_key = os.environ.get(self.ENV_VAR_API_KEY)
        if env_key:
            if self.validator.is_valid_format(env_key):
                self.logger.info("API key loaded from environment variable")
                return env_key, StorageMethod.ENVIRONMENT
            else:
                self.logger.warning(
                    "Invalid API key format found in environment variable"
                )

        # 3. Check encrypted file storage (fallback)
        try:
            file_key = self.encrypted_storage.get_api_key()
            if file_key:
                if self.validator.is_valid_format(file_key):
                    self.logger.info("API key loaded from encrypted file storage")
                    return file_key, StorageMethod.ENCRYPTED_FILE
                else:
                    self.logger.warning(
                        "Invalid API key format found in encrypted file storage"
                    )
        except Exception as e:
            self.logger.error(f"Error reading from encrypted file storage: {e}")

        # 4. No valid key found
        self.logger.info("No valid API key found in any storage location")
        return None, StorageMethod.NOT_FOUND

    def store_api_key(
        self, api_key: str, preferred_method: StorageMethod | None = None
    ) -> tuple[bool, StorageMethod, str | None]:
        """Store API key using preferred method with fallback.

        Args:
            api_key: The API key to store
            preferred_method: Preferred storage method, defaults to encrypted_file

        Returns:
            Tuple of (success, actual_method_used, error_message)
        """
        if not self.validator.is_valid_format(api_key):
            return False, StorageMethod.NOT_FOUND, "Invalid API key format"

        try:
            self.encrypted_storage.store_api_key(api_key)
            self.logger.info("API key stored in encrypted file storage")
            return True, StorageMethod.ENCRYPTED_FILE, None
        except Exception as e:
            error_msg = f"Encrypted file storage failed: {e}"
            self.logger.error(error_msg)
            return False, StorageMethod.NOT_FOUND, error_msg

    def delete_api_key(self, method: StorageMethod | None = None) -> tuple[bool, str]:
        """Delete API key from storage.

        Args:
            method: Specific method to delete from, or None to delete from all

        Returns:
            Tuple of (success, message)
        """
        results = []

        if method is None or method == StorageMethod.ENCRYPTED_FILE:
            try:
                if self.encrypted_storage.delete_api_key():
                    results.append("Deleted from encrypted file")
                    self.logger.info("API key deleted from encrypted file storage")
            except Exception as e:
                results.append(f"File deletion error: {e}")

        # We don't delete environment variables as they're typically managed externally

        if results:
            return True, "; ".join(results)
        else:
            return False, "No API keys found to delete"

    def get_storage_status(self) -> dict[str, Any]:
        """Get status of API key storage across all methods.

        Returns:
            Dictionary with storage method status information
        """
        status: dict[str, Any] = {
            "environment": {
                "available": bool(os.environ.get(self.ENV_VAR_API_KEY)),
                "valid": False,
            },
            "encrypted_file": {"available": False, "valid": False, "error": None},
            "current_source": StorageMethod.NOT_FOUND.value,
        }

        # Check environment
        env_key = os.environ.get(self.ENV_VAR_API_KEY)
        if env_key:
            status["environment"]["valid"] = self.validator.is_valid_format(env_key)
            if status["environment"]["valid"]:
                status["current_source"] = StorageMethod.ENVIRONMENT.value

        # Check encrypted file
        try:
            file_key = self.encrypted_storage.get_api_key()
            if file_key:
                status["encrypted_file"]["available"] = True
                status["encrypted_file"]["valid"] = self.validator.is_valid_format(
                    file_key
                )
                if (
                    status["encrypted_file"]["valid"]
                    and status["current_source"] == StorageMethod.NOT_FOUND.value
                ):
                    status["current_source"] = StorageMethod.ENCRYPTED_FILE.value
        except Exception as e:
            status["encrypted_file"]["error"] = str(e)

        return status

    def update_api_key(
        self, new_api_key: str, preferred_method: StorageMethod | None = None
    ) -> tuple[bool, StorageMethod, str | None]:
        """Update existing API key with a new one.

        Args:
            new_api_key: New API key to store
            preferred_method: Preferred storage method

        Returns:
            Tuple of (success, method_used, error_message)
        """
        current_key, current_method = self.get_api_key()

        if current_method != StorageMethod.NOT_FOUND:
            self.delete_api_key(current_method)

        return self.store_api_key(new_api_key, preferred_method)
