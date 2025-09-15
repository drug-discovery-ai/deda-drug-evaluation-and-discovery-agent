"""Encrypted file storage fallback for API keys."""

import json
import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet

CONFIG_KEY_STORAGE_METHOD = "storage_method"

CONFIG_ENCRYPTED_API_KEY = "encrypted_api_key"


class EncryptedFileStorage:
    """Encrypted file-based storage for API keys as a fallback option."""

    def __init__(self, app_data_dir: Path):
        """Initialize encrypted file storage.

        Args:
            app_data_dir: Directory for application data
        """
        self.app_data_dir = Path(app_data_dir)
        self.config_file = self.app_data_dir / "config.json"
        self.key_file = self.app_data_dir / ".encryption_key"
        self.logger = logging.getLogger(__name__)

        self._ensure_app_data_dir()

    def _ensure_app_data_dir(self) -> None:
        """Ensure the app data directory exists with proper permissions."""
        if not self.app_data_dir.exists():
            self.app_data_dir.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(self.app_data_dir, 0o700)
            except OSError as e:
                self.logger.warning(f"Could not set directory permissions: {e}")

    def _get_encryption_key(self) -> bytes:
        """Get or create encryption key for this installation.

        Returns:
            Encryption key as bytes
        """
        if self.key_file.exists():
            try:
                with open(self.key_file, "rb") as f:
                    key: bytes = f.read()
                    Fernet(key)  # This will raise an exception if invalid
                    return key
            except Exception as e:
                self.logger.warning(
                    f"Invalid encryption key found, generating new one: {e}"
                )

        key = Fernet.generate_key()
        try:
            with open(self.key_file, "wb") as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)
            self.logger.info("Generated new encryption key")
        except OSError as e:
            self.logger.error(f"Could not save encryption key: {e}")
            raise

        return key

    def store_api_key(self, api_key: str) -> None:
        """Store API key in encrypted file.

        Args:
            api_key: The API key to store

        Raises:
            Exception: If storage fails
        """
        try:
            encryption_key = self._get_encryption_key()
            fernet = Fernet(encryption_key)

            encrypted_key = fernet.encrypt(api_key.encode("utf-8"))

            config_data = {
                CONFIG_ENCRYPTED_API_KEY: encrypted_key.decode("utf-8"),
                CONFIG_KEY_STORAGE_METHOD: "encrypted_file",
            }

            with open(self.config_file, "w") as f:
                json.dump(config_data, f, indent=2)

            os.chmod(self.config_file, 0o600)

            self.logger.info("API key stored in encrypted file")

        except Exception as e:
            self.logger.error(f"Failed to store API key in encrypted file: {e}")
            raise

    def get_api_key(self) -> str | None:
        """Retrieve API key from encrypted file.

        Returns:
            Decrypted API key or None if not found/invalid

        Raises:
            Exception: If decryption fails due to file corruption
        """
        if not self.config_file.exists():
            return None

        try:
            with open(self.config_file) as f:
                config_data = json.load(f)

            if CONFIG_ENCRYPTED_API_KEY not in config_data:
                self.logger.warning("No encrypted_api_key found in config file")
                return None

            encryption_key = self._get_encryption_key()
            fernet = Fernet(encryption_key)

            encrypted_key_bytes = config_data[CONFIG_ENCRYPTED_API_KEY].encode("utf-8")
            decrypted_key: bytes = fernet.decrypt(encrypted_key_bytes)

            self.logger.debug("API key retrieved from encrypted file")
            return decrypted_key.decode("utf-8")

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to decrypt API key: {e}")
            # Don't raise here, just return None to allow other storage methods
            return None

    def delete_api_key(self) -> bool:
        """Delete stored API key while preserving config file structure.

        Returns:
            True if key was deleted, False if no key existed
        """
        deleted = False

        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config_data = json.load(f)

                # Remove only the API key, keep other config data
                if CONFIG_ENCRYPTED_API_KEY in config_data:
                    del config_data[CONFIG_ENCRYPTED_API_KEY]

                    with open(self.config_file, "w") as f:
                        json.dump(config_data, f, indent=2)

                    os.chmod(self.config_file, 0o600)
                    deleted = True
                    self.logger.info("Removed API key from config file")
                else:
                    self.logger.info("No API key found in config file")

            except (json.JSONDecodeError, OSError) as e:
                self.logger.error(f"Could not modify config file: {e}")

        # Still delete the encryption key file since it's only used for the API key
        if self.key_file.exists():
            try:
                self.key_file.unlink()
                deleted = True
                self.logger.info("Deleted encryption key file")
            except OSError as e:
                self.logger.error(f"Could not delete key file: {e}")

        return deleted
