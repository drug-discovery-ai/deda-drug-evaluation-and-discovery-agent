"""Tests for API key storage and retrieval service."""

import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from drug_discovery_agent.key_storage.key_manager import APIKeyManager, StorageMethod


class TestAPIKeyManager:
    """Test cases for APIKeyManager."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Store original environment variable to restore later
        self.original_env_api_key = os.environ.get(APIKeyManager.ENV_VAR_API_KEY)

        # Clean up environment variables at start
        if APIKeyManager.ENV_VAR_API_KEY in os.environ:
            del os.environ[APIKeyManager.ENV_VAR_API_KEY]

        # Patch the user data directory to use temp directory
        with patch.object(APIKeyManager, "_get_user_data_dir") as mock_get_dir:
            mock_get_dir.return_value = Path(self.temp_dir)
            self.manager = APIKeyManager()

        # Ensure encrypted storage starts clean
        try:
            self.manager.encrypted_storage.delete_api_key()
        except Exception:
            pass  # Ignore if file doesn't exist

        self.test_api_key = "sk-1234567890abcdefghij"

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        # Clean up environment variables
        if APIKeyManager.ENV_VAR_API_KEY in os.environ:
            del os.environ[APIKeyManager.ENV_VAR_API_KEY]

        # Restore original environment variable if it existed
        if self.original_env_api_key is not None:
            os.environ[APIKeyManager.ENV_VAR_API_KEY] = self.original_env_api_key

        # Clean up temp directory
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_user_data_dir_platform_specific(self) -> None:
        """Test platform-specific user data directory selection."""
        manager = APIKeyManager()

        with patch("platform.system") as mock_system:
            # Test macOS
            mock_system.return_value = "Darwin"
            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path("/Users/test")
                data_dir = manager._get_user_data_dir()
                assert "Library/Application Support" in str(data_dir)

            # Test Windows
            mock_system.return_value = "Windows"
            with patch.dict(os.environ, {"APPDATA": "/Users/test/AppData/Roaming"}):
                data_dir = manager._get_user_data_dir()
                assert "AppData" in str(data_dir)

            # Test Linux
            mock_system.return_value = "Linux"
            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path("/home/test")
                data_dir = manager._get_user_data_dir()
                assert ".config" in str(data_dir)

    def test_get_api_key_from_environment(self) -> None:
        """Test retrieving API key from environment variable."""
        # Set environment variable
        os.environ[APIKeyManager.ENV_VAR_API_KEY] = self.test_api_key

        key, source = self.manager.get_api_key()
        assert key == self.test_api_key
        assert source == StorageMethod.ENVIRONMENT

    def test_get_api_key_environment_invalid_format(self) -> None:
        """Test handling invalid API key format in environment."""
        # Set invalid key in environment
        os.environ[APIKeyManager.ENV_VAR_API_KEY] = "invalid"

        key, source = self.manager.get_api_key()
        # Should skip invalid environment key and continue to other methods
        assert source != StorageMethod.ENVIRONMENT

    @patch("keyring.get_password")
    def test_get_api_key_from_keychain(self, mock_get_password: Any) -> None:
        """Test retrieving API key from OS keychain."""
        # Mock keychain to return our test key
        mock_get_password.return_value = self.test_api_key

        key, source = self.manager.get_api_key()
        assert key == self.test_api_key
        assert source == StorageMethod.KEYCHAIN

        # Verify keyring was called correctly
        mock_get_password.assert_called_once_with(
            APIKeyManager.SERVICE_NAME, APIKeyManager.ACCOUNT_NAME
        )

    @patch("keyring.get_password")
    def test_get_api_key_keychain_error(self, mock_get_password: Any) -> None:
        """Test handling keychain access errors."""
        from keyring.errors import KeyringError

        mock_get_password.side_effect = KeyringError("Access denied")

        key, source = self.manager.get_api_key()
        # Should fall back to other methods
        assert source != StorageMethod.KEYCHAIN

    @patch("keyring.get_password")
    def test_get_api_key_from_encrypted_file(self, mock_get_password: Any) -> None:
        """Test retrieving API key from encrypted file storage."""
        # Mock keyring to return None (no key in keychain)
        mock_get_password.return_value = None

        # Store key in encrypted file first
        self.manager.encrypted_storage.store_api_key(self.test_api_key)

        key, source = self.manager.get_api_key()
        assert key == self.test_api_key
        assert source == StorageMethod.ENCRYPTED_FILE

    @patch("keyring.get_password")
    @patch.dict("os.environ", {}, clear=True)
    def test_get_api_key_not_found(self, mock_get_password: Any) -> None:
        """Test when no API key is found anywhere."""
        # Mock keyring to return None
        mock_get_password.return_value = None

        # Mock encrypted storage to return None
        with patch.object(
            self.manager.encrypted_storage, "get_api_key", return_value=None
        ):
            key, source = self.manager.get_api_key()
            assert key is None
            assert source == StorageMethod.NOT_FOUND

    def test_priority_order(self) -> None:
        """Test that environment variable takes priority over other methods."""
        # Set up keys in multiple locations - use valid key format
        os.environ[APIKeyManager.ENV_VAR_API_KEY] = "sk-envkey1234567890abcdef"
        self.manager.encrypted_storage.store_api_key("sk-filekey1234567890abcdef")

        with patch("keyring.get_password") as mock_keyring:
            mock_keyring.return_value = "sk-keychainkey1234567890ab"

            key, source = self.manager.get_api_key()
            assert key == "sk-envkey1234567890abcdef"
            assert source == StorageMethod.ENVIRONMENT

    @patch("keyring.set_password")
    def test_store_api_key_keychain(self, mock_set_password: Any) -> None:
        """Test storing API key in keychain."""
        success, method, error = self.manager.store_api_key(self.test_api_key)

        assert success
        assert method == StorageMethod.KEYCHAIN
        assert error is None

        mock_set_password.assert_called_once_with(
            APIKeyManager.SERVICE_NAME, APIKeyManager.ACCOUNT_NAME, self.test_api_key
        )

    @patch("keyring.set_password")
    def test_store_api_key_keychain_fallback(self, mock_set_password: Any) -> None:
        """Test fallback to encrypted file when keychain fails."""
        from keyring.errors import KeyringError

        mock_set_password.side_effect = KeyringError("Access denied")

        success, method, error = self.manager.store_api_key(self.test_api_key)

        assert success
        assert method == StorageMethod.ENCRYPTED_FILE
        assert error is None

        # Verify key was stored in encrypted file
        retrieved = self.manager.encrypted_storage.get_api_key()
        assert retrieved == self.test_api_key

    def test_store_api_key_invalid_format(self) -> None:
        """Test storing invalid API key format."""
        success, method, error = self.manager.store_api_key("invalid")

        assert not success
        assert method == StorageMethod.NOT_FOUND
        assert error and "Invalid API key format" in error

    def test_store_api_key_preferred_method(self) -> None:
        """Test storing with preferred method."""
        # Test with encrypted file as preferred method
        success, method, error = self.manager.store_api_key(
            self.test_api_key, StorageMethod.ENCRYPTED_FILE
        )

        assert success
        assert method == StorageMethod.ENCRYPTED_FILE
        assert error is None

    @patch("keyring.delete_password")
    def test_delete_api_key_all_methods(self, mock_delete_password: Any) -> None:
        """Test deleting API key from all storage methods."""
        # Store key in encrypted file
        self.manager.encrypted_storage.store_api_key(self.test_api_key)

        success, message = self.manager.delete_api_key()

        assert success
        assert "Deleted from" in message

        # Verify keyring delete was called
        mock_delete_password.assert_called_once()

        # Verify encrypted file was deleted
        assert self.manager.encrypted_storage.get_api_key() is None

    @patch("keyring.delete_password")
    def test_delete_api_key_specific_method(self, mock_delete_password: Any) -> None:
        """Test deleting API key from specific storage method."""
        success, message = self.manager.delete_api_key(StorageMethod.KEYCHAIN)

        # Should only call keyring delete
        mock_delete_password.assert_called_once()

    @patch("keyring.get_password")
    def test_get_storage_status(self, mock_get_password: Any) -> None:
        """Test getting storage status across all methods."""
        # Mock keyring to return None initially
        mock_get_password.return_value = None

        # Initially all should be empty
        status = self.manager.get_storage_status()

        assert not status["environment"]["available"]
        assert not status["keychain"]["available"]
        assert not status["encrypted_file"]["available"]
        assert status["current_source"] == StorageMethod.NOT_FOUND.value

        # Add environment key
        os.environ[APIKeyManager.ENV_VAR_API_KEY] = self.test_api_key
        status = self.manager.get_storage_status()

        assert status["environment"]["available"]
        assert status["environment"]["valid"]
        assert status["current_source"] == StorageMethod.ENVIRONMENT.value

    @patch("keyring.get_password")
    def test_storage_status_with_keychain(self, mock_get_password: Any) -> None:
        """Test storage status with keychain key."""
        mock_get_password.return_value = self.test_api_key

        status = self.manager.get_storage_status()

        assert status["keychain"]["available"]
        assert status["keychain"]["valid"]

    def test_storage_status_with_encrypted_file(self) -> None:
        """Test storage status with encrypted file key."""
        self.manager.encrypted_storage.store_api_key(self.test_api_key)

        status = self.manager.get_storage_status()

        assert status["encrypted_file"]["available"]
        assert status["encrypted_file"]["valid"]

    def test_update_api_key(self) -> None:
        """Test updating existing API key."""
        # Store initial key
        self.manager.encrypted_storage.store_api_key(self.test_api_key)

        # Update with new key
        new_key = "sk-9876543210zyxwvutsrq"
        success, method, error = self.manager.update_api_key(new_key)

        assert success
        assert error is None

        # Verify new key is stored
        retrieved, source = self.manager.get_api_key()
        assert retrieved == new_key

    def test_validation_integration(self) -> None:
        """Test integration with validation module."""
        # The manager should use validator for format checking
        assert hasattr(self.manager, "validator")

        # Invalid key should be rejected
        success, method, error = self.manager.store_api_key("invalid")
        assert not success

        # Valid key should be accepted
        success, method, error = self.manager.store_api_key(self.test_api_key)
        assert success

    @patch("keyring.get_password")
    @patch("keyring.set_password")
    def test_error_handling(
        self, mock_set_password: Any, mock_get_password: Any
    ) -> None:
        """Test error handling for various failure scenarios."""
        # Test keyring get_password error
        mock_get_password.side_effect = Exception("Unexpected error")
        key, source = self.manager.get_api_key()
        # Should handle gracefully and continue to other methods

        # Test keyring set_password error
        mock_set_password.side_effect = Exception("Unexpected error")
        # Should fall back to encrypted file
        success, method, error = self.manager.store_api_key(self.test_api_key)
        assert success  # Should succeed with encrypted file fallback
        assert method == StorageMethod.ENCRYPTED_FILE

    def test_concurrent_access(self) -> None:
        """Test handling of concurrent access scenarios."""
        # This is a basic test - in reality, more sophisticated
        # concurrent testing would be needed

        # Store key
        success1, method1, error1 = self.manager.store_api_key(self.test_api_key)

        # Create another manager instance (simulating another process)
        with patch.object(APIKeyManager, "_get_user_data_dir") as mock_get_dir:
            mock_get_dir.return_value = Path(self.temp_dir)
            manager2 = APIKeyManager()

        # Should be able to read the same key
        key2, source2 = manager2.get_api_key()
        assert key2 == self.test_api_key
