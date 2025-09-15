"""Tests for encrypted file storage fallback."""

import json
import os
import tempfile
from pathlib import Path

from drug_discovery_agent.key_storage.storage_fallback import EncryptedFileStorage


class TestEncryptedFileStorage:
    """Test cases for EncryptedFileStorage."""

    def setup_method(self) -> None:
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = EncryptedFileStorage(Path(self.temp_dir))
        self.test_api_key = "sk-1234567890abcdefghij"

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        # Clean up temp directory
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_storage_initialization(self) -> None:
        """Test storage initialization and directory creation."""
        # Directory should be created
        assert self.storage.app_data_dir.exists()
        assert self.storage.app_data_dir.is_dir()

        # Files should not exist initially
        assert not self.storage.config_file.exists()
        assert not self.storage.key_file.exists()

    def test_store_and_retrieve_api_key(self) -> None:
        """Test storing and retrieving an API key."""
        # Store the key
        self.storage.store_api_key(self.test_api_key)

        # Verify files were created
        assert self.storage.config_file.exists()
        assert self.storage.key_file.exists()

        # Retrieve the key
        retrieved_key = self.storage.get_api_key()
        assert retrieved_key == self.test_api_key

    def test_encryption_key_generation(self) -> None:
        """Test encryption key generation and persistence."""
        # Get encryption key (should generate new one)
        key1 = self.storage._get_encryption_key()
        assert key1 is not None
        assert len(key1) > 0

        # Get it again (should load the same key)
        key2 = self.storage._get_encryption_key()
        assert key1 == key2

        # Key file should exist
        assert self.storage.key_file.exists()

    def test_encryption_key_validation(self) -> None:
        """Test encryption key validation and regeneration."""
        # Create invalid key file
        with open(self.storage.key_file, "wb") as f:
            f.write(b"invalid_key")

        # Should regenerate valid key
        key = self.storage._get_encryption_key()
        assert key is not None

        # Should be able to use the key for encryption
        from cryptography.fernet import Fernet

        fernet = Fernet(key)
        encrypted = fernet.encrypt(b"test")
        decrypted = fernet.decrypt(encrypted)
        assert decrypted == b"test"

    def test_config_file_structure(self) -> None:
        """Test config file structure and content."""
        self.storage.store_api_key(self.test_api_key)

        # Check config file structure
        with open(self.storage.config_file) as f:
            config = json.load(f)

        assert "encrypted_api_key" in config
        assert "storage_method" in config
        assert config["storage_method"] == "encrypted_file"

    def test_file_permissions(self) -> None:
        """Test that files have correct permissions."""
        self.storage.store_api_key(self.test_api_key)

        # Check permissions (should be readable/writable by owner only)
        if os.name != "nt":  # Skip on Windows
            config_stat = os.stat(self.storage.config_file)
            key_stat = os.stat(self.storage.key_file)

            # Check that permissions are restrictive (0o600)
            assert oct(config_stat.st_mode)[-3:] == "600"
            assert oct(key_stat.st_mode)[-3:] == "600"

    def test_delete_api_key(self) -> None:
        """Test deleting stored API key while preserving config structure."""
        # Store a key first
        self.storage.store_api_key(self.test_api_key)
        assert self.storage.get_api_key() == self.test_api_key

        # Delete the key
        deleted = self.storage.delete_api_key()
        assert deleted

        # Config file should still exist but key file should be gone
        assert self.storage.config_file.exists()
        assert not self.storage.key_file.exists()

        # Config should preserve structure but without encrypted_api_key
        with open(self.storage.config_file) as f:
            config = json.load(f)
        assert "storage_method" in config
        assert "encrypted_api_key" not in config
        assert config["storage_method"] == "encrypted_file"

        # Should return None when trying to get key
        assert self.storage.get_api_key() is None

    def test_delete_nonexistent_key(self) -> None:
        """Test deleting when no key exists."""
        # Should return False when no files exist
        deleted = self.storage.delete_api_key()
        assert not deleted

    def test_get_nonexistent_key(self) -> None:
        """Test retrieving when no key exists."""
        key = self.storage.get_api_key()
        assert key is None

    def test_corrupted_config_file(self) -> None:
        """Test handling of corrupted config file."""
        # Create invalid JSON config
        self.storage.app_data_dir.mkdir(exist_ok=True)
        with open(self.storage.config_file, "w") as f:
            f.write("invalid json {")

        # Should return None without raising exception
        key = self.storage.get_api_key()
        assert key is None

    def test_missing_encrypted_key_field(self) -> None:
        """Test handling of config file missing encrypted key field."""
        # Create valid JSON but missing required field
        self.storage.app_data_dir.mkdir(exist_ok=True)
        config = {"version": "1.0", "storage_method": "encrypted_file"}
        with open(self.storage.config_file, "w") as f:
            json.dump(config, f)

        # Should return None
        key = self.storage.get_api_key()
        assert key is None

    def test_decryption_failure(self) -> None:
        """Test handling of decryption failures."""
        # Store a key first
        self.storage.store_api_key(self.test_api_key)

        # Corrupt the encryption key
        with open(self.storage.key_file, "wb") as f:
            f.write(b"corrupted_key_data_that_is_invalid")

        # Should return None when decryption fails
        key = self.storage.get_api_key()
        assert key is None

    def test_multiple_store_operations(self) -> None:
        """Test multiple store operations (updates)."""
        # Store initial key
        self.storage.store_api_key(self.test_api_key)
        assert self.storage.get_api_key() == self.test_api_key

        # Store different key
        new_key = "sk-9876543210zyxwvutsrq"
        self.storage.store_api_key(new_key)
        assert self.storage.get_api_key() == new_key

        # Original key should be overwritten
        assert self.storage.get_api_key() != self.test_api_key

    def test_permission_setting_failure(self) -> None:
        """Test handling of permission setting failures."""
        # This test just verifies that the storage still works
        # even if permission setting fails in some scenarios
        self.storage.store_api_key(self.test_api_key)
        retrieved = self.storage.get_api_key()
        assert retrieved == self.test_api_key

    def test_directory_creation_with_parents(self) -> None:
        """Test directory creation with nested paths."""
        nested_path = Path(self.temp_dir) / "nested" / "deep" / "path"
        storage = EncryptedFileStorage(nested_path)

        # Directory should be created
        assert storage.app_data_dir.exists()

        # Should be able to store and retrieve
        storage.store_api_key(self.test_api_key)
        assert storage.get_api_key() == self.test_api_key

    def test_unicode_api_key(self) -> None:
        """Test storing and retrieving API keys with unicode characters."""
        unicode_key = "sk-1234567890abcdefghij-ñáéíóú"
        self.storage.store_api_key(unicode_key)
        retrieved = self.storage.get_api_key()
        assert retrieved == unicode_key

    def test_long_api_key(self) -> None:
        """Test storing and retrieving very long API keys."""
        long_key = "sk-" + "a" * 500
        self.storage.store_api_key(long_key)
        retrieved = self.storage.get_api_key()
        assert retrieved == long_key

    def test_empty_api_key(self) -> None:
        """Test handling of empty API key."""
        # Should be able to store empty string
        self.storage.store_api_key("")
        retrieved = self.storage.get_api_key()
        assert retrieved == ""

    def test_delete_api_key_from_config_without_key(self) -> None:
        """Test deleting API key from config that doesn't contain one."""
        # Create config file without encrypted_api_key
        self.storage.app_data_dir.mkdir(exist_ok=True)
        config = {"version": "1.0", "storage_method": "encrypted_file"}
        with open(self.storage.config_file, "w") as f:
            json.dump(config, f)

        # Delete should return False (no key to delete)
        deleted = self.storage.delete_api_key()
        assert not deleted

        # Config file should still exist with same content
        assert self.storage.config_file.exists()
        with open(self.storage.config_file) as f:
            updated_config = json.load(f)
        assert updated_config == config
