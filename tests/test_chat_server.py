"""Tests for stateful chat server functionality."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from drug_discovery_agent.chat_server import (
    ChatRequest,
    ChatResponse,
    ChatServer,
)


class TestChatServerModels:
    """Test suite for Pydantic models used by the chat server."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "message,expected_valid",
        [
            ("Hello world", True),
            ("", True),  # Empty string is valid
            ("A" * 10000, True),  # Very long message is valid
            ("Special chars: !@#$%^&*()", True),
            ("Unicode: 🧬🔬💊", True),
        ],
    )
    def test_chat_request_validation(self, message: str, expected_valid: bool) -> None:
        """Test ChatRequest model validation."""
        session_id = "test-session-123"
        if expected_valid:
            request = ChatRequest(session_id=session_id, message=message)
            assert request.message == message
            assert request.session_id == session_id
        else:
            with pytest.raises(ValueError):
                ChatRequest(session_id=session_id, message=message)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "response,expected_valid",
        [
            ("Response message", True),
            ("", True),  # Empty response is valid
            ("Very long response: " + "A" * 10000, True),
            ("Error: Something went wrong", True),
            ("JSON response: {'key': 'value'}", True),
        ],
    )
    def test_chat_response_validation(
        self, response: str, expected_valid: bool
    ) -> None:
        """Test ChatResponse model validation."""
        session_id = "test-session-456"
        if expected_valid:
            chat_response = ChatResponse(session_id=session_id, response=response)
            assert chat_response.response == response
            assert chat_response.session_id == session_id
        else:
            with pytest.raises(ValueError):
                ChatResponse(session_id=session_id, response=response)

    @pytest.mark.unit
    def test_chat_request_serialization(self) -> None:
        """Test ChatRequest model serialization."""
        request = ChatRequest(session_id="test-123", message="Test message")
        serialized = request.model_dump()
        assert serialized == {"session_id": "test-123", "message": "Test message"}

        # Test JSON serialization
        json_str = request.model_dump_json()
        assert json_str == '{"session_id":"test-123","message":"Test message"}'

    @pytest.mark.unit
    def test_chat_response_serialization(self) -> None:
        """Test ChatResponse model serialization."""
        response = ChatResponse(session_id="test-456", response="Test response")
        serialized = response.model_dump()
        assert serialized == {"session_id": "test-456", "response": "Test response"}

        # Test JSON serialization
        json_str = response.model_dump_json()
        assert json_str == '{"session_id":"test-456","response":"Test response"}'


class TestChatServerSessionManagement:
    """Test suite for session management endpoints."""

    @pytest.fixture
    def chat_server(self) -> ChatServer:
        """Create chat server instance."""
        return ChatServer(verbose=False)

    @pytest.fixture
    def test_client(self, chat_server: ChatServer) -> TestClient:
        """Create test client for the chat server."""
        app = chat_server.create_app()
        return TestClient(app)

    @pytest.mark.unit
    def test_create_session(self, test_client: TestClient) -> None:
        """Test session creation endpoint."""
        response = test_client.post("/api/sessions", json={"verbose": False})

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert isinstance(data["session_id"], str)
        assert len(data["session_id"]) > 0

    @pytest.mark.unit
    def test_create_session_verbose(self, test_client: TestClient) -> None:
        """Test session creation with verbose mode."""
        response = test_client.post("/api/sessions", json={"verbose": True})

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data

    @pytest.mark.unit
    def test_delete_session(self, test_client: TestClient) -> None:
        """Test session deletion endpoint."""
        # Create a session first
        create_response = test_client.post("/api/sessions", json={"verbose": False})
        session_id = create_response.json()["session_id"]

        # Delete the session
        delete_response = test_client.delete(f"/api/sessions/{session_id}")

        assert delete_response.status_code == 200
        data = delete_response.json()
        assert "message" in data
        assert session_id in data["message"]

    @pytest.mark.unit
    def test_delete_nonexistent_session(self, test_client: TestClient) -> None:
        """Test deleting a non-existent session."""
        response = test_client.delete("/api/sessions/nonexistent-session")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    @pytest.mark.unit
    def test_get_session_info(self, test_client: TestClient) -> None:
        """Test getting session information."""
        # Create a session first
        create_response = test_client.post("/api/sessions", json={"verbose": False})
        session_id = create_response.json()["session_id"]

        # Get session info
        info_response = test_client.get(f"/api/sessions/{session_id}/info")

        assert info_response.status_code == 200
        data = info_response.json()
        assert data["session_id"] == session_id
        assert "created_at" in data
        assert "last_accessed" in data
        assert "message_count" in data
        assert data["message_count"] == 0
        assert data["is_active"] is True

    @pytest.mark.unit
    def test_get_nonexistent_session_info(self, test_client: TestClient) -> None:
        """Test getting info for non-existent session."""
        response = test_client.get("/api/sessions/nonexistent-session/info")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    @pytest.mark.unit
    def test_clear_session_conversation(self, test_client: TestClient) -> None:
        """Test clearing session conversation history."""
        # Create a session first
        create_response = test_client.post("/api/sessions", json={"verbose": False})
        session_id = create_response.json()["session_id"]

        # Clear the conversation
        clear_response = test_client.post(f"/api/sessions/{session_id}/clear")

        assert clear_response.status_code == 200
        data = clear_response.json()
        assert "message" in data
        assert session_id in data["message"]

    @pytest.mark.unit
    def test_clear_nonexistent_session_conversation(
        self, test_client: TestClient
    ) -> None:
        """Test clearing conversation for non-existent session."""
        response = test_client.post("/api/sessions/nonexistent-session/clear")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data


class TestChatServerEndpoints:
    """Test suite for chat server endpoints."""

    @pytest.fixture
    def chat_server(self) -> ChatServer:
        """Create chat server instance."""
        return ChatServer(verbose=False)

    @pytest.fixture
    def test_client(self, chat_server: ChatServer) -> TestClient:
        """Create test client for the chat server."""
        app = chat_server.create_app()
        return TestClient(app)

    @pytest.mark.unit
    def test_health_check(self, test_client: TestClient) -> None:
        """Test health check endpoint."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "bioinformatics-chat-server"
        assert data["version"] == "1.0.0"

    @pytest.mark.unit
    @patch("drug_discovery_agent.chat_server.session_manager.BioinformaticsChatClient")
    def test_chat_endpoint_success(
        self, mock_client_class: MagicMock, test_client: TestClient
    ) -> None:
        """Test successful chat endpoint interaction."""
        # Setup mock
        mock_client = AsyncMock()
        mock_client.chat.return_value = "Test response from chat client"
        mock_client_class.return_value = mock_client

        # Create a session first
        session_response = test_client.post("/api/sessions", json={"verbose": False})
        assert session_response.status_code == 200
        session_id = session_response.json()["session_id"]

        # Make chat request with session_id
        response = test_client.post(
            "/api/chat",
            json={"session_id": session_id, "message": "Hello, test message"},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["response"] == "Test response from chat client"

        # Verify client was created and called correctly
        mock_client_class.assert_called_once_with(verbose=False)
        mock_client.chat.assert_called_once_with("Hello, test message")

    @pytest.mark.unit
    def test_chat_endpoint_invalid_json(self, test_client: TestClient) -> None:
        """Test chat endpoint with invalid JSON."""
        response = test_client.post(
            "/api/chat",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    @pytest.mark.unit
    def test_chat_endpoint_missing_session_id(self, test_client: TestClient) -> None:
        """Test chat endpoint with missing session_id field."""
        response = test_client.post("/api/chat", json={"message": "test"})

        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    @pytest.mark.unit
    def test_chat_endpoint_missing_message_field(self, test_client: TestClient) -> None:
        """Test chat endpoint with missing message field."""
        response = test_client.post("/api/chat", json={"session_id": "test-session"})

        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    @pytest.mark.unit
    @patch("drug_discovery_agent.chat_server.session_manager.BioinformaticsChatClient")
    def test_chat_endpoint_client_error(
        self, mock_client_class: MagicMock, test_client: TestClient
    ) -> None:
        """Test chat endpoint when BioinformaticsChatClient raises an error."""
        # Setup mock to raise exception
        mock_client = AsyncMock()
        mock_client.chat.side_effect = Exception("Chat client error")
        mock_client_class.return_value = mock_client

        # Create a session first
        session_response = test_client.post("/api/sessions", json={"verbose": False})
        session_id = session_response.json()["session_id"]

        response = test_client.post(
            "/api/chat", json={"session_id": session_id, "message": "Test message"}
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "Chat client error" in data["error"]

    @pytest.mark.unit
    def test_chat_endpoint_invalid_session(self, test_client: TestClient) -> None:
        """Test chat endpoint with invalid session_id."""
        response = test_client.post(
            "/api/chat",
            json={"session_id": "invalid-session", "message": "Test message"},
        )

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "not found" in data["error"]


class TestChatServerStreaming:
    """Test suite for streaming chat functionality."""

    @pytest.fixture
    def chat_server(self) -> ChatServer:
        """Create chat server instance."""
        return ChatServer(verbose=False)

    @pytest.fixture
    def test_client(self, chat_server: ChatServer) -> TestClient:
        """Create test client for the chat server."""
        app = chat_server.create_app()
        return TestClient(app)

    @pytest.mark.unit
    @patch("drug_discovery_agent.chat_server.session_manager.BioinformaticsChatClient")
    def test_chat_stream_endpoint_success(
        self, mock_client_class: MagicMock, test_client: TestClient
    ) -> None:
        """Test streaming chat endpoint."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client.chat.return_value = "Hello world!"
        mock_client_class.return_value = mock_client

        # Create a session first
        session_response = test_client.post("/api/sessions", json={"verbose": False})
        assert session_response.status_code == 200
        session_id = session_response.json()["session_id"]

        # Make streaming request
        response = test_client.post(
            "/api/chat/stream",
            json={"session_id": session_id, "message": "Test streaming message"},
        )

        # Verify response
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        # Parse the streaming response
        content = response.text
        assert "data: " in content

        # Check for expected content chunks
        lines = content.strip().split("\n")
        data_lines = [line for line in lines if line.startswith("data: ")]

        # Should have processing, content, and completion signals
        assert len(data_lines) >= 3  # Processing + content + done signals

        # Verify JSON structure in data lines
        for line in data_lines[:3]:  # Check first few data lines
            data_content = line[6:]  # Remove "data: " prefix
            parsed = json.loads(data_content)
            assert "type" in parsed
            assert "data" in parsed

    @pytest.mark.unit
    def test_chat_stream_endpoint_invalid_json(self, test_client: TestClient) -> None:
        """Test streaming chat endpoint with invalid JSON."""
        response = test_client.post(
            "/api/chat/stream",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    @pytest.mark.unit
    @patch("drug_discovery_agent.chat_server.session_manager.BioinformaticsChatClient")
    def test_chat_stream_endpoint_error_handling(
        self, mock_client_class: MagicMock, test_client: TestClient
    ) -> None:
        """Test streaming endpoint error handling."""
        # Setup mock to fail
        mock_client_class.side_effect = Exception("Stream setup failed")

        response = test_client.post(
            "/api/chat/stream",
            json={"session_id": "test-session", "message": "Test message"},
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        # The error should be in the stream content
        content = response.text
        assert "data: " in content
        assert "error" in content


class TestChatServerCORS:
    """Test suite for CORS configuration."""

    @pytest.fixture
    def chat_server(self) -> ChatServer:
        """Create chat server instance."""
        return ChatServer(verbose=False)

    @pytest.fixture
    def test_client(self, chat_server: ChatServer) -> TestClient:
        """Create test client for the chat server."""
        app = chat_server.create_app()
        return TestClient(app)

    @pytest.mark.unit
    def test_cors_middleware_configuration(self, chat_server: ChatServer) -> None:
        """Test that CORS middleware is properly configured."""
        from starlette.middleware.cors import CORSMiddleware

        app = chat_server.create_app()

        # Verify CORS middleware is in the middleware stack
        cors_middleware_found = False
        for middleware in app.user_middleware:
            if middleware.cls == CORSMiddleware:
                cors_middleware_found = True
                # Verify configuration
                kwargs = middleware.kwargs
                expected_origins = [
                    "http://localhost:3000",
                    "app://electron-app",
                    "http://127.0.0.1:3000",
                ]
                for origin in expected_origins:
                    assert origin in kwargs["allow_origins"]
                assert "GET" in kwargs["allow_methods"]
                assert "POST" in kwargs["allow_methods"]
                assert kwargs["allow_headers"] == ["*"]
                break

        assert cors_middleware_found, "CORS middleware not found in middleware stack"

    @pytest.mark.unit
    def test_cors_preflight_request(self, test_client: TestClient) -> None:
        """Test CORS preflight request handling."""
        response = test_client.options(
            "/api/chat",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        # CORS preflight should be handled
        assert response.status_code in [200, 204]


class TestChatServerIntegration:
    """Integration tests for the chat server."""

    @pytest.fixture
    def chat_server(self) -> ChatServer:
        """Create chat server instance."""
        return ChatServer(verbose=True)  # Test with verbose=True

    @pytest.fixture
    def test_client(self, chat_server: ChatServer) -> TestClient:
        """Create test client for the chat server."""
        app = chat_server.create_app()
        return TestClient(app)

    @pytest.mark.integration
    def test_server_initialization_with_verbose(self, chat_server: ChatServer) -> None:
        """Test server initialization with verbose mode."""
        assert chat_server.verbose is True
        app = chat_server.create_app()
        assert app is not None

    @pytest.mark.integration
    def test_all_endpoints_accessible(self, test_client: TestClient) -> None:
        """Test that all defined endpoints are accessible."""
        # Test health endpoint
        health_response = test_client.get("/health")
        assert health_response.status_code == 200

        # Test chat endpoint (should fail validation but not 404)
        chat_response = test_client.post("/api/chat", json={})
        assert (
            chat_response.status_code != 404
        )  # Should be validation error, not not found

        # Test streaming endpoint (should fail validation but not 404)
        stream_response = test_client.post("/api/chat/stream", json={})
        assert (
            stream_response.status_code != 404
        )  # Should be validation error, not not found

    @pytest.mark.integration
    @patch("drug_discovery_agent.chat_server.session_manager.BioinformaticsChatClient")
    def test_verbose_mode_affects_client_creation(
        self, mock_client_class: MagicMock, test_client: TestClient
    ) -> None:
        """Test that verbose mode is passed to BioinformaticsChatClient."""
        # Setup mock
        mock_client = AsyncMock()
        mock_client.chat.return_value = "Test response"
        mock_client_class.return_value = mock_client

        # Create a session with verbose=True
        session_response = test_client.post("/api/sessions", json={"verbose": True})
        session_id = session_response.json()["session_id"]

        # Make request
        response = test_client.post(
            "/api/chat", json={"session_id": session_id, "message": "test"}
        )

        # Verify client was created with verbose=True
        mock_client_class.assert_called_with(verbose=True)
        assert response.status_code == 200


class TestChatServerStateful:
    """Test suite to verify stateful behavior."""

    @pytest.fixture
    def chat_server(self) -> ChatServer:
        """Create chat server instance."""
        return ChatServer(verbose=False)

    @pytest.fixture
    def test_client(self, chat_server: ChatServer) -> TestClient:
        """Create test client for the chat server."""
        app = chat_server.create_app()
        return TestClient(app)

    @pytest.mark.unit
    @patch("drug_discovery_agent.chat_server.session_manager.BioinformaticsChatClient")
    def test_client_reused_per_session(
        self, mock_client_class: MagicMock, test_client: TestClient
    ) -> None:
        """Test that BioinformaticsChatClient is reused within a session."""
        # Setup mock
        mock_client = AsyncMock()
        mock_client.chat.return_value = "Response"
        mock_client_class.return_value = mock_client

        # Create a session
        session_response = test_client.post("/api/sessions", json={"verbose": False})
        session_id = session_response.json()["session_id"]

        # Make multiple requests with the same session
        test_client.post(
            "/api/chat", json={"session_id": session_id, "message": "First request"}
        )
        test_client.post(
            "/api/chat", json={"session_id": session_id, "message": "Second request"}
        )
        test_client.post(
            "/api/chat", json={"session_id": session_id, "message": "Third request"}
        )

        # Verify only one client created for the session
        assert mock_client_class.call_count == 1
        assert mock_client.chat.call_count == 3

    @pytest.mark.unit
    @patch("drug_discovery_agent.chat_server.session_manager.BioinformaticsChatClient")
    def test_streaming_endpoint_stateful(
        self, mock_client_class: MagicMock, test_client: TestClient
    ) -> None:
        """Test that streaming endpoint reuses client within session."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client.chat.return_value = "Test response"
        mock_client_class.return_value = mock_client

        # Create two different sessions
        session1_response = test_client.post("/api/sessions", json={"verbose": False})
        session1_id = session1_response.json()["session_id"]

        session2_response = test_client.post("/api/sessions", json={"verbose": False})
        session2_id = session2_response.json()["session_id"]

        # Make streaming requests to different sessions
        test_client.post(
            "/api/chat/stream", json={"session_id": session1_id, "message": "Stream 1"}
        )
        test_client.post(
            "/api/chat/stream", json={"session_id": session2_id, "message": "Stream 2"}
        )

        # Verify one client created per session
        assert mock_client_class.call_count == 2
