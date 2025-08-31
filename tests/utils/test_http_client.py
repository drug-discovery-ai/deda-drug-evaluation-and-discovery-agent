from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from drug_discovery_agent.utils.http_client import make_api_request, make_fasta_request


class TestHttpClient:
    """Test suite for HTTP client functions."""

    @pytest.mark.unit
    @patch("httpx.AsyncClient")
    async def test_make_api_request_json_success(
        self, mock_client_cls: Any, http_mock_helpers: Any
    ) -> None:
        """Test successful JSON API request."""
        expected_response = {"key": "value", "data": [1, 2, 3]}

        mock_response = http_mock_helpers.create_mock_http_response(
            response_data=expected_response
        )
        mock_async_client = AsyncMock()
        mock_async_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_async_client

        result = await make_api_request("https://example.com/api")

        assert result == expected_response
        mock_response.raise_for_status.assert_called_once()

    @pytest.mark.unit
    @patch("httpx.AsyncClient")
    async def test_make_api_request_text_success(
        self, mock_client_cls: Any, http_mock_helpers: Any
    ) -> None:
        """Test successful text API request."""
        expected_text = "This is plain text response"

        mock_response = http_mock_helpers.create_mock_http_response(
            response_data=None, text_data=expected_text
        )
        mock_async_client = AsyncMock()
        mock_async_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_async_client

        result = await make_api_request(
            "https://example.com/api", accept_format="text/plain"
        )

        assert result == expected_text
        mock_response.raise_for_status.assert_called_once()

    @pytest.mark.unit
    @patch("httpx.AsyncClient")
    async def test_make_api_request_headers(self, mock_client_cls: Any, http_mock_helpers: Any) -> None:
        """Test API request with headers - custom, default, and override scenarios."""
        expected_response = {"status": "ok"}

        mock_response = http_mock_helpers.create_mock_http_response(
            response_data=expected_response
        )
        mock_async_client = AsyncMock()
        mock_async_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_async_client

        # Test 1: Custom headers with defaults
        custom_headers = {"Authorization": "Bearer token123"}
        result = await make_api_request(
            "https://example.com/api", headers=custom_headers
        )

        assert result == expected_response
        call_args = mock_async_client.get.call_args
        headers = call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer token123"
        assert "User-Agent" in headers
        assert headers["Accept"] == "application/json"

        # Test 2: Override default headers
        override_headers = {
            "Accept": "application/xml",
            "User-Agent": "Custom-Agent/1.0",
        }
        await make_api_request("https://example.com/api", headers=override_headers)

        call_args = mock_async_client.get.call_args
        headers = call_args.kwargs["headers"]
        assert headers["Accept"] == "application/xml"
        assert headers["User-Agent"] == "Custom-Agent/1.0"

        # Test 3: Default headers only
        mock_async_client.reset_mock()
        await make_api_request("https://example.com/api")

        call_args = mock_async_client.get.call_args
        headers = call_args.kwargs["headers"]
        assert "User-Agent" in headers
        assert headers["Accept"] == "application/json"

    @pytest.mark.unit
    @patch("httpx.AsyncClient")
    async def test_make_api_request_with_timeout(
        self, mock_client_cls: Any, http_mock_helpers: Any
    ) -> None:
        """Test API request with custom timeout."""
        expected_response = {"data": "test"}

        mock_response = http_mock_helpers.create_mock_http_response(
            response_data=expected_response
        )
        mock_async_client = AsyncMock()
        mock_async_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_async_client

        result = await make_api_request("https://example.com/api", timeout=60.0)

        assert result == expected_response
        call_args = mock_async_client.get.call_args
        assert call_args.kwargs["timeout"] == 60.0

    @pytest.mark.unit
    @patch("httpx.AsyncClient")
    @pytest.mark.parametrize(
        "error_type,error_instance",
        [
            ("http_error", None),  # Will use fixture
            ("timeout_error", None),  # Will use fixture
            ("connection_error", None),  # Will use fixture
            ("json_decode_error", None),  # Special case for JSON decode error
        ],
    )
    async def test_make_api_request_errors(
        self,
        mock_client_cls: Any,
        error_type: str,
        error_instance: Any,
        common_http_errors: Any,
        http_mock_helpers: Any,
    ) -> None:
        """Test API request error handling - HTTP, timeout, connection, and JSON decode errors."""
        mock_async_client = AsyncMock()

        if error_type == "json_decode_error":

            def raise_error() -> None:
                raise ValueError("Invalid JSON")

            mock_response = AsyncMock()
            mock_response.json = raise_error
            mock_response.raise_for_status = AsyncMock()
            mock_async_client.get.return_value = mock_response
        elif error_type == "http_error":
            mock_async_client.get.side_effect = common_http_errors["not_found"]
        elif error_type == "timeout_error":
            mock_async_client.get.side_effect = common_http_errors["timeout"]
        elif error_type == "connection_error":
            mock_async_client.get.side_effect = common_http_errors["connection_error"]

        mock_client_cls.return_value.__aenter__.return_value = mock_async_client

        result = await make_api_request("https://example.com/api")

        assert result is None

    @pytest.mark.unit
    @patch("drug_discovery_agent.utils.http_client.make_api_request")
    @pytest.mark.parametrize(
        "return_value,expected_result",
        [
            (
                """>sp|P0DTC2|SPIKE_SARS2 Spike glycoprotein
MFVFLVLLPLVSSQCVNLTTRTQLPPAYTNSFTRGVYYPDKVFRSSVLHSTQDLFLPFFSNVTWFHAIH""",
                """>sp|P0DTC2|SPIKE_SARS2 Spike glycoprotein
MFVFLVLLPLVSSQCVNLTTRTQLPPAYTNSFTRGVYYPDKVFRSSVLHSTQDLFLPFFSNVTWFHAIH""",
            ),
            (None, None),
        ],
    )
    async def test_make_fasta_request(
        self, mock_request: Any, return_value: str | None, expected_result: str | None
    ) -> None:
        """Test FASTA request success and failure scenarios."""
        mock_request.return_value = return_value

        result = await make_fasta_request("https://example.com/protein.fasta")

        assert result == expected_result
        mock_request.assert_called_once_with(
            "https://example.com/protein.fasta", accept_format="text/plain"
        )

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_make_api_request_real_request(self) -> None:
        """Integration test with real HTTP request."""
        # Test with a reliable public API
        result = await make_api_request("https://httpbin.org/json", timeout=10.0)

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_make_fasta_request_real_request(self) -> None:
        """Integration test with real FASTA request."""
        # Test with a simple text endpoint
        result = await make_fasta_request("https://httpbin.org/robots.txt")

        assert result is not None
        assert isinstance(result, str)
