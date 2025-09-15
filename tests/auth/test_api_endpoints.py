"""Tests for API key management endpoints."""

import tempfile
from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from drug_discovery_agent.key_storage.key_manager import StorageMethod
from drug_discovery_agent.settings.api_key.settings import create_api_key_routes


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    import shutil

    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_key_manager(temp_dir: str) -> Generator[Mock, None, None]:
    """Create mock key manager with temporary directory."""
    with patch(
        "drug_discovery_agent.settings.api_key.settings.APIKeyManager"
    ) as mock_manager_class:
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        yield mock_manager


@pytest.fixture
def client(mock_key_manager: Mock) -> TestClient:
    """Create test client with API routes."""
    routes = create_api_key_routes()
    app = Starlette(routes=routes)
    return TestClient(app)


class TestAPIKeyEndpoints:
    """Test cases for API key management endpoints."""

    def test_store_api_key_success(
        self, client: TestClient, mock_key_manager: Mock
    ) -> None:
        """Test successful API key storage."""
        # Mock successful storage
        mock_key_manager.store_api_key.return_value = (
            True,
            StorageMethod.KEYCHAIN,
            None,
        )

        # Mock validation
        with patch(
            "drug_discovery_agent.settings.api_key.settings.APIKeyValidator"
        ) as mock_validator_class:
            mock_validator = Mock()
            mock_validator_class.return_value = mock_validator
            mock_validator.validate_for_storage.return_value = (True, [], [])

            response = client.post(
                "/api/key", json={"api_key": "sk-1234567890abcdefghij"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["method_used"] == "keychain"

    def test_store_api_key_invalid_format(
        self, client: TestClient, mock_key_manager: Mock
    ) -> None:
        """Test storing invalid API key format."""
        with patch(
            "drug_discovery_agent.settings.api_key.settings.APIKeyValidator"
        ) as mock_validator_class:
            mock_validator = Mock()
            mock_validator_class.return_value = mock_validator
            mock_validator.validate_for_storage.return_value = (
                False,
                [],
                ["Invalid API key format"],
            )

            response = client.post("/api/key", json={"api_key": "invalid"})

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "Invalid API key" in data["message"]

    def test_store_api_key_with_preferred_method(
        self, client: TestClient, mock_key_manager: Mock
    ) -> None:
        """Test storing API key with preferred method."""
        mock_key_manager.store_api_key.return_value = (
            True,
            StorageMethod.ENCRYPTED_FILE,
            None,
        )

        with patch(
            "drug_discovery_agent.settings.api_key.settings.APIKeyValidator"
        ) as mock_validator_class:
            mock_validator = Mock()
            mock_validator_class.return_value = mock_validator
            mock_validator.validate_for_storage.return_value = (True, [], [])

            response = client.post(
                "/api/key",
                json={
                    "api_key": "sk-1234567890abcdefghij",
                    "preferred_method": "encrypted_file",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["method_used"] == "encrypted_file"

        # Verify the preferred method was passed
        mock_key_manager.store_api_key.assert_called_with(
            "sk-1234567890abcdefghij", StorageMethod.ENCRYPTED_FILE
        )

    def test_store_api_key_invalid_preferred_method(
        self, client: TestClient, mock_key_manager: Mock
    ) -> None:
        """Test storing API key with invalid preferred method."""
        response = client.post(
            "/api/key",
            json={
                "api_key": "sk-1234567890abcdefghij",
                "preferred_method": "invalid_method",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "Invalid storage method" in data["message"]

    def test_get_key_status_with_key(
        self, client: TestClient, mock_key_manager: Mock
    ) -> None:
        """Test getting key status when key exists."""
        mock_key_manager.get_api_key.return_value = (
            "sk-1234567890abcdefghij",
            StorageMethod.KEYCHAIN,
        )
        mock_key_manager.get_storage_status.return_value = {
            "environment": {"available": False, "valid": False},
            "keychain": {"available": True, "valid": True},
            "encrypted_file": {"available": False, "valid": False},
            "current_source": "keychain",
        }

        with patch(
            "drug_discovery_agent.settings.api_key.settings.APIKeyValidator"
        ) as mock_validator_class:
            mock_validator = Mock()
            mock_validator_class.return_value = mock_validator
            mock_validator.mask_api_key.return_value = "sk-1***************ghij"

            response = client.get("/api/key/status")

        assert response.status_code == 200
        data = response.json()
        assert data["has_key"] is True
        assert data["source"] == "keychain"
        assert data["masked_key"] == "sk-1***************ghij"

    def test_get_key_status_no_key(
        self, client: TestClient, mock_key_manager: Mock
    ) -> None:
        """Test getting key status when no key exists."""
        mock_key_manager.get_api_key.return_value = (None, StorageMethod.NOT_FOUND)
        mock_key_manager.get_storage_status.return_value = {
            "environment": {"available": False, "valid": False},
            "keychain": {"available": False, "valid": False},
            "encrypted_file": {"available": False, "valid": False},
            "current_source": "not_found",
        }

        response = client.get("/api/key/status")

        assert response.status_code == 200
        data = response.json()
        assert data["has_key"] is False
        assert data["source"] == "not_found"
        assert data["masked_key"] is None

    def test_delete_api_key_success(
        self, client: TestClient, mock_key_manager: Mock
    ) -> None:
        """Test successful API key deletion."""
        mock_key_manager.delete_api_key.return_value = (
            True,
            "Deleted from keychain; Deleted from encrypted file",
        )

        response = client.delete("/api/key")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Deleted from" in data["message"]

    def test_delete_api_key_no_keys_found(
        self, client: TestClient, mock_key_manager: Mock
    ) -> None:
        """Test deleting when no keys exist."""
        mock_key_manager.delete_api_key.return_value = (
            False,
            "No API keys found to delete",
        )

        response = client.delete("/api/key")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "No API keys found" in data["message"]

    def test_validate_api_key_valid(
        self, client: TestClient, mock_key_manager: Mock
    ) -> None:
        """Test API key validation for valid key."""
        with patch(
            "drug_discovery_agent.settings.api_key.settings.APIKeyValidator"
        ) as mock_validator_class:
            mock_validator = Mock()
            mock_validator_class.return_value = mock_validator
            mock_validator.validate_for_storage.return_value = (True, [], [])
            mock_validator.get_security_recommendations.return_value = [
                "Never share your API key",
                "Store securely",
            ]

            response = client.post(
                "/api/key/validate",
                json={"api_key": "sk-1234567890abcdefghij"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["format_type"] == "openai"
        assert len(data["recommendations"]) > 0

    def test_validate_api_key_invalid(
        self, client: TestClient, mock_key_manager: Mock
    ) -> None:
        """Test API key validation for invalid key."""
        with patch(
            "drug_discovery_agent.settings.api_key.settings.APIKeyValidator"
        ) as mock_validator_class:
            mock_validator = Mock()
            mock_validator_class.return_value = mock_validator
            mock_validator.validate_for_storage.return_value = (
                False,
                [],
                ["API key is too short (minimum 23 characters)"],
            )

            response = client.post("/api/key/validate", json={"api_key": "invalid"})

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert data["format_type"] == "unknown"
        assert data["error_message"] == "API key is too short (minimum 23 characters)"

    def test_update_api_key_success(
        self, client: TestClient, mock_key_manager: Mock
    ) -> None:
        """Test successful API key update."""
        mock_key_manager.update_api_key.return_value = (
            True,
            StorageMethod.KEYCHAIN,
            None,
        )

        with patch(
            "drug_discovery_agent.settings.api_key.settings.APIKeyValidator"
        ) as mock_validator_class:
            mock_validator = Mock()
            mock_validator_class.return_value = mock_validator
            mock_validator.validate_for_storage.return_value = (True, [], [])

            response = client.put(
                "/api/key", json={"api_key": "sk-9876543210zyxwvutsrq"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["method_used"] == "keychain"

    def test_update_api_key_failure(
        self, client: TestClient, mock_key_manager: Mock
    ) -> None:
        """Test API key update failure."""
        mock_key_manager.update_api_key.return_value = (
            False,
            StorageMethod.NOT_FOUND,
            "Storage failed",
        )

        with patch(
            "drug_discovery_agent.settings.api_key.settings.APIKeyValidator"
        ) as mock_validator_class:
            mock_validator = Mock()
            mock_validator_class.return_value = mock_validator
            mock_validator.validate_for_storage.return_value = (True, [], [])

            response = client.put(
                "/api/key", json={"api_key": "sk-9876543210zyxwvutsrq"}
            )

        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert "Storage failed" in data["message"]

    def test_invalid_json_request(
        self, client: TestClient, mock_key_manager: Mock
    ) -> None:
        """Test handling of invalid JSON requests."""
        response = client.post(
            "/api/key",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 500  # Our API returns 500 for JSON errors

    def test_missing_required_fields(
        self, client: TestClient, mock_key_manager: Mock
    ) -> None:
        """Test handling of missing required fields."""
        response = client.post(
            "/api/key",
            json={},  # Missing api_key field
        )

        assert response.status_code == 500  # Our API handles this as internal error

    def test_empty_api_key(self, client: TestClient, mock_key_manager: Mock) -> None:
        """Test handling of empty API key."""
        response = client.post("/api/key", json={"api_key": ""})

        assert response.status_code == 500  # Our API handles this as internal error

    def test_internal_error_handling(
        self, client: TestClient, mock_key_manager: Mock
    ) -> None:
        """Test handling of internal errors."""
        mock_key_manager.store_api_key.side_effect = Exception("Database error")

        with patch(
            "drug_discovery_agent.settings.api_key.settings.APIKeyValidator"
        ) as mock_validator_class:
            mock_validator = Mock()
            mock_validator_class.return_value = mock_validator
            mock_validator.validate_for_storage.return_value = (True, [], [])

            response = client.post(
                "/api/key", json={"api_key": "sk-1234567890abcdefghij"}
            )

        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert "Internal error" in data["message"]

    def test_api_key_with_warnings(
        self, client: TestClient, mock_key_manager: Mock
    ) -> None:
        """Test storing API key that has warnings but is valid."""
        mock_key_manager.store_api_key.return_value = (
            True,
            StorageMethod.KEYCHAIN,
            None,
        )

        with patch(
            "drug_discovery_agent.settings.api_key.settings.APIKeyValidator"
        ) as mock_validator_class:
            mock_validator = Mock()
            mock_validator_class.return_value = mock_validator
            mock_validator.validate_for_storage.return_value = (
                True,
                ["API key is relatively short"],
                [],
            )

            response = client.post(
                "/api/key", json={"api_key": "sk-1234567890abcdefghij"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["warnings"] is not None
        assert len(data["warnings"]) > 0
