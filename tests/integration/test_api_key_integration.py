"""Integration tests for the complete API key workflow."""

import os
import random
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from drug_discovery_agent.chat_server.server import ChatServer
from drug_discovery_agent.interfaces.langchain.chat_client import (
    BioinformaticsChatClient,
)
from drug_discovery_agent.key_storage.key_manager import APIKeyManager, StorageMethod


class TestAPIKeyIntegration:
    """Integration tests for the complete API key workflow."""

    def setup_method(self) -> None:
        """Set up test environment for each test."""
        # Create temporary directory for test storage
        self.temp_dir = tempfile.mkdtemp()

        # Use test-specific service and account names to avoid conflicts
        self.test_service_name = (
            f"drug_discovery_agent_test_{random.randint(1000, 9999)}"
        )
        self.test_account_name = f"openai_api_key_test_{random.randint(1000, 9999)}"

        # Patch the service and account names for this test
        self.service_patch = patch.object(
            APIKeyManager, "SERVICE_NAME", self.test_service_name
        )
        self.account_patch = patch.object(
            APIKeyManager, "ACCOUNT_NAME", self.test_account_name
        )
        self.service_patch.start()
        self.account_patch.start()

        # Set environment variable to use temp directory for all APIKeyManager instances
        self.original_data_dir = os.environ.get("DRUG_DISCOVERY_AGENT_DATA_DIR")
        os.environ["DRUG_DISCOVERY_AGENT_DATA_DIR"] = self.temp_dir

        # Create test key manager (will use temp directory via env var)
        self.key_manager = APIKeyManager()

        # Ensure clean state by deleting all keys
        try:
            self.key_manager.delete_api_key()  # Delete from all storage methods
        except Exception:
            pass  # Ignore if keys don't exist

        # Clear environment variables for clean testing
        self.original_api_key = os.environ.get("API_KEY")
        self.original_openai_key = os.environ.get("OPENAI_API_KEY")

        # Remove API keys from environment
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

    def teardown_method(self) -> None:
        """Clean up after each test."""
        # Clear any stored keys from all storage methods
        try:
            self.key_manager.delete_api_key()
        except Exception:
            pass

        # Stop patches
        self.service_patch.stop()
        self.account_patch.stop()

        # Clean up test storage
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Restore original environment variables
        if self.original_api_key:
            os.environ["API_KEY"] = self.original_api_key
        if self.original_openai_key:
            os.environ["OPENAI_API_KEY"] = self.original_openai_key
        if self.original_data_dir:
            os.environ["DRUG_DISCOVERY_AGENT_DATA_DIR"] = self.original_data_dir
        elif "DRUG_DISCOVERY_AGENT_DATA_DIR" in os.environ:
            del os.environ["DRUG_DISCOVERY_AGENT_DATA_DIR"]

    def test_startup_with_environment_api_key(self) -> None:
        """Test server startup with API key in environment variable."""
        # Set environment variable
        test_key = "sk-test123456789abcdef123456789abcdef"
        os.environ["OPENAI_API_KEY"] = test_key

        # Check startup key availability
        from drug_discovery_agent.chat_server.server import check_api_key_availability

        has_key, message, source = check_api_key_availability()

        assert has_key
        assert source == StorageMethod.ENVIRONMENT
        assert "environment" in message

    def test_startup_with_stored_api_key(self) -> None:
        """Test server startup with API key in storage."""
        # Store API key
        test_key = "sk-test123456789abcdef123456789abcdef"
        success, method, _ = self.key_manager.store_api_key(test_key)

        if not success:
            pytest.skip("Keychain access not available in test environment")

        # Check startup key availability using the same manager instance
        api_key, source = self.key_manager.get_api_key()

        assert api_key is not None
        assert source in [StorageMethod.KEYCHAIN, StorageMethod.ENCRYPTED_FILE]

    def test_startup_without_api_key(self) -> None:
        """Test server startup without any API key."""
        # Ensure no keys are present
        assert not os.environ.get("API_KEY")
        assert not os.environ.get("OPENAI_API_KEY")

        # Check startup key availability
        from drug_discovery_agent.chat_server.server import check_api_key_availability

        has_key, message, source = check_api_key_availability()

        assert not has_key
        assert source == StorageMethod.NOT_FOUND

    def test_api_key_storage_endpoints(self) -> None:
        """Test API key storage through REST endpoints."""
        # Create test server
        server = ChatServer()
        app = server.create_app()

        with TestClient(app) as client:
            # Test storing API key
            test_key = "sk-test123456789abcdef123456789abcdef"
            response = client.post(
                "/api/key",
                json={"api_key": test_key, "preferred_method": "encrypted_file"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "encrypted_file" in data["method_used"]

            # Test getting key status
            response = client.get("/api/key/status")
            assert response.status_code == 200
            data = response.json()
            assert data["has_key"] is True
            assert data["masked_key"] is not None

            # Test key validation
            response = client.post("/api/key/validate", json={"api_key": test_key})
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True

            # Test updating key
            new_key = "sk-test987654321fedcba987654321fedcba"
            response = client.put("/api/key", json={"api_key": new_key})
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Test deleting key
            response = client.delete("/api/key")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_chat_client_api_key_integration(self) -> None:
        """Test that chat client properly uses stored API keys."""
        # Store a test API key
        test_key = "sk-test123456789abcdef123456789abcdef"
        success, _, _ = self.key_manager.store_api_key(test_key)
        assert success

        # Mock the OpenAI client to avoid actual API calls
        with patch("langchain_openai.ChatOpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Create chat client - this should not raise any exceptions if API key is available
            try:
                chat_client = BioinformaticsChatClient()
                # Chat client creation successful
                assert chat_client is not None
            except ValueError as e:
                if "No API key found" in str(e):
                    pytest.fail("Chat client should have found the stored API key")
                else:
                    raise

    def test_api_key_priority_order(self) -> None:
        """Test that API key priority order is respected."""
        # Store a key in encrypted storage
        stored_key = "sk-stored123456789abcdef123456789abcdef"
        success, method, _ = self.key_manager.store_api_key(stored_key)
        assert success
        # Method could be either keychain or encrypted file depending on system
        assert method in [StorageMethod.KEYCHAIN, StorageMethod.ENCRYPTED_FILE]

        # Set environment variable (higher priority)
        env_key = "sk-enviro123456789abcdef123456789abcdef"
        os.environ["OPENAI_API_KEY"] = env_key

        # Get API key - should return environment key
        retrieved_key, source = self.key_manager.get_api_key()
        assert retrieved_key == env_key
        assert source == StorageMethod.ENVIRONMENT

        # Remove environment variable
        del os.environ["OPENAI_API_KEY"]

        # Get API key again - should return stored key
        retrieved_key, source = self.key_manager.get_api_key()
        assert retrieved_key == stored_key
        assert source in [StorageMethod.KEYCHAIN, StorageMethod.ENCRYPTED_FILE]

    def test_invalid_api_key_handling(self) -> None:
        """Test handling of invalid API keys."""
        server = ChatServer()
        app = server.create_app()

        with TestClient(app) as client:
            # Try to store invalid API key
            invalid_keys = [
                "invalid",
                "sk-a",  # Too short (only 4 chars, need 5+)
                "not-sk-prefix123456789abcdef123456789abcdef",
            ]

            for invalid_key in invalid_keys:
                response = client.post("/api/key", json={"api_key": invalid_key})

                assert response.status_code == 400
                data = response.json()
                assert data["success"] is False
                assert "Invalid API key" in data["message"]

            # Test empty string separately (causes validation error)
            response = client.post("/api/key", json={"api_key": ""})
            # Empty string causes a validation error before reaching our handler
            assert response.status_code in [400, 422, 500]

    @pytest.mark.asyncio
    async def test_complete_user_workflow(self) -> None:
        """Test complete user workflow from key storage to chat usage."""
        # Step 1: Store API key via REST API
        server = ChatServer()
        app = server.create_app()

        test_key = "sk-test123456789abcdef123456789abcdef"

        with TestClient(app) as client:
            # Store API key
            response = client.post("/api/key", json={"api_key": test_key})
            assert response.status_code == 200
            assert response.json()["success"] is True

            # Verify key status
            response = client.get("/api/key/status")
            assert response.status_code == 200
            status_data = response.json()
            assert status_data["has_key"] is True

        # Step 2: Verify chat client can use the stored key
        with patch("langchain_openai.ChatOpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Create chat client - this should not raise any exceptions if API key is available
            try:
                chat_client = BioinformaticsChatClient()
                # Chat client creation successful
                assert chat_client is not None
            except ValueError as e:
                if "No API key found" in str(e):
                    pytest.fail("Chat client should have found the stored API key")
                else:
                    raise

        # Step 3: Verify that chat client was created successfully
        # Note: The chat client creates its own model instance internally

        # Step 4: Test key refresh functionality
        new_key = "sk-new9876543210fedcba9876543210fedcba"
        with TestClient(app) as client:
            response = client.put("/api/key", json={"api_key": new_key})
            assert response.status_code == 200

        # Step 5: Verify new key was stored (refresh functionality not implemented)
        # Note: API key refresh functionality is not implemented in BioinformaticsChatClient
        # The chat client would need to be recreated to use the new key
        retrieved_key, source = self.key_manager.get_api_key()
        assert retrieved_key == new_key

    def test_concurrent_api_key_access(self) -> None:
        """Test concurrent access to API key storage."""
        import tempfile
        import threading

        # Use same key for all threads to test proper concurrency handling
        test_key = "sk-test123456789abcdef123456789abcdef"
        results = []
        lock = threading.Lock()

        def store_and_retrieve(thread_id: int) -> None:
            try:
                # Create separate manager for each thread with its own temp directory
                thread_temp_dir = tempfile.mkdtemp()
                thread_manager = APIKeyManager()
                thread_manager.encrypted_storage.config_file = (
                    Path(thread_temp_dir) / "config.json"
                )

                # Add small random delay to simulate real-world conditions
                time.sleep(random.uniform(0.001, 0.01))

                # Store key (preferring encrypted file to avoid keychain conflicts)
                success, method, _ = thread_manager.store_api_key(
                    test_key, preferred_method=StorageMethod.ENCRYPTED_FILE
                )

                if success:
                    # Small delay to simulate real usage
                    time.sleep(random.uniform(0.001, 0.005))

                    # Retrieve key
                    retrieved_key, source = thread_manager.get_api_key()

                    # Clean up thread temp directory
                    import shutil

                    shutil.rmtree(thread_temp_dir, ignore_errors=True)

                    with lock:
                        # Should retrieve the same key that was stored
                        results.append(
                            retrieved_key == test_key
                            and source == StorageMethod.ENCRYPTED_FILE
                        )
                else:
                    # Clean up thread temp directory
                    import shutil

                    shutil.rmtree(thread_temp_dir, ignore_errors=True)

                    with lock:
                        results.append(False)

            except Exception as e:
                # Log the exception for debugging
                print(f"Thread {thread_id} failed: {e}")
                with lock:
                    results.append(False)

        # Run multiple threads concurrently
        threads = []
        for i in range(3):
            thread = threading.Thread(target=store_and_retrieve, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete with timeout
        for thread in threads:
            thread.join(timeout=10.0)
            if thread.is_alive():
                # Force thread to stop if it's taking too long
                with lock:
                    results.append(False)

        # All operations should succeed since each thread uses isolated storage
        success_count = sum(results)
        assert success_count >= 2, (
            f"Expected at least 2 successes, got {success_count}: {results}"
        )
        assert len(results) == 3

    def test_error_handling_and_recovery(self) -> None:
        """Test error handling and recovery scenarios."""
        server = ChatServer()
        app = server.create_app()

        with TestClient(app) as client:
            # Test malformed JSON
            response = client.post("/api/key", content="invalid json")
            assert response.status_code in [
                400,
                422,
                500,
            ]  # Various frameworks handle this differently

            # Test missing required fields
            response = client.post("/api/key", json={})
            assert response.status_code in [400, 422, 500]  # Missing required field

            # Test getting status when no key exists
            response = client.get("/api/key/status")
            assert response.status_code == 200
            data = response.json()
            assert data["has_key"] is False

            # Ensure no keys exist by trying to delete them first
            response = client.delete("/api/key")
            assert response.status_code == 200

            # Test deleting non-existent key again
            response = client.delete("/api/key")
            assert response.status_code == 200
            data = response.json()
            # Should still return success with appropriate message
            assert "No API keys found to delete" in data["message"]
