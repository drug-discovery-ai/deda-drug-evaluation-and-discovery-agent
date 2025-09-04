"""Mock HTTP server fixtures for testing external API calls."""

import json
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import respx
from httpx import Response


class MockHttpServer:
    """A mock HTTP server that can simulate various API responses."""

    def __init__(self) -> None:
        self.mock = respx.mock
        self._routes: dict[str, dict[str, Any]] = {}

    def add_route(
        self,
        method: str,
        url: str,
        response_data: Any = None,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        text: str | None = None,
        delay: float = 0.0,
    ) -> None:
        """Add a mock route to the server.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL pattern to match
            response_data: JSON response data
            status_code: HTTP status code to return
            headers: Additional response headers
            text: Raw text response (alternative to response_data)
            delay: Delay in seconds before responding
        """
        route_key = f"{method.upper()}:{url}"
        self._routes[route_key] = {
            "method": method.upper(),
            "url": url,
            "response_data": response_data,
            "status_code": status_code,
            "headers": headers or {},
            "text": text,
            "delay": delay,
        }

    def start(self) -> None:
        """Start the mock server and register all routes."""
        self.mock.start()

        for route_config in self._routes.values():
            method = route_config["method"]
            url = route_config["url"]

            if route_config["text"]:
                content = route_config["text"]
                content_type = "text/plain"
            else:
                content = (
                    json.dumps(route_config["response_data"])
                    if route_config["response_data"]
                    else ""
                )
                content_type = "application/json"

            headers = {"Content-Type": content_type, **route_config["headers"]}

            # Register the route with respx
            if method == "GET":
                self.mock.get(url).mock(
                    return_value=Response(
                        status_code=route_config["status_code"],
                        headers=headers,
                        content=content,
                    )
                )
            elif method == "POST":
                self.mock.post(url).mock(
                    return_value=Response(
                        status_code=route_config["status_code"],
                        headers=headers,
                        content=content,
                    )
                )
            # Add more methods as needed

    def stop(self) -> None:
        """Stop the mock server."""
        self.mock.stop()

    def reset(self) -> None:
        """Reset all routes and stop the server."""
        self.mock.reset()
        self._routes.clear()


@pytest.fixture
def mock_http_server() -> Generator[MockHttpServer, None, None]:
    """Provide a mock HTTP server for testing."""
    server = MockHttpServer()
    yield server
    server.stop()
    server.reset()


@pytest.fixture
async def async_mock_http_server() -> AsyncGenerator[MockHttpServer, None]:
    """Provide an async mock HTTP server for testing."""
    server = MockHttpServer()
    yield server
    server.stop()
    server.reset()


class CommonApiMocks:
    """Pre-configured mock responses for common APIs and scenarios."""

    @staticmethod
    def httpbin_json() -> dict[str, Any]:
        """Mock response for httpbin.org/json endpoint."""
        return {
            "slideshow": {
                "author": "Test Author",
                "date": "2024-01-01",
                "slides": [
                    {"title": "Test Slide 1", "type": "all"},
                    {
                        "title": "Test Slide 2",
                        "type": "all",
                        "items": ["Item 1", "Item 2"],
                    },
                ],
                "title": "Test Slideshow",
            }
        }

    @staticmethod
    def httpbin_robots_txt() -> str:
        """Mock response for httpbin.org/robots.txt endpoint."""
        return """User-agent: *
Disallow: /deny
Allow: /
"""

    @staticmethod
    def uniprot_fasta(protein_id: str = "P0DTC2") -> str:
        """Mock FASTA response for UniProt protein."""
        return f""">sp|{protein_id}|SPIKE_SARS2 Spike glycoprotein OS=Test organism
MFVFLVLLPLVSSQCVNLTTRTQLPPAYTNSFTRGVYYPDKVFRSSVLHSTQDLFLPFFSNVT
WFHAIHVSGTNGTKRFDNPVLPFNDGVYFASTEKSNIIRGWIFGTTLDSKTQSLLIVNNATN
"""

    @staticmethod
    def uniprot_json(protein_id: str = "P0DTC2") -> dict[str, Any]:
        """Mock JSON response for UniProt protein data."""
        return {
            "results": [
                {
                    "uniProtKBAccession": protein_id,
                    "entryName": "SPIKE_SARS2",
                    "proteinDescription": {
                        "recommendedName": {"fullName": {"value": "Spike glycoprotein"}}
                    },
                    "organism": {"scientificName": "Test organism", "taxonId": 12345},
                    "sequence": {
                        "value": "MFVFLVLLPLVSSQCVNLTTRTQLPPAYTNSFTRGVYYPDKVFRSSVLH",
                        "length": 48,
                        "molWeight": 5432,
                    },
                }
            ]
        }

    @staticmethod
    def pdb_json(pdb_id: str = "6VSB") -> dict[str, Any]:
        """Mock JSON response for PDB structure data."""
        return {
            "data": [
                {
                    "rcsb_id": pdb_id,
                    "struct": {
                        "title": "Test protein structure",
                        "pdbx_descriptor": "Test protein",
                    },
                    "rcsb_entry_info": {
                        "resolution_combined": [2.85],
                        "structure_determination_methodology": "X-RAY DIFFRACTION",
                        "experimental_method": "X-RAY DIFFRACTION",
                    },
                }
            ]
        }

    @staticmethod
    def error_response(
        status_code: int = 404, message: str = "Not Found"
    ) -> dict[str, Any]:
        """Mock error response."""
        return {"error": message, "status_code": status_code}


@pytest.fixture
def common_api_mocks() -> CommonApiMocks:
    """Provide common API mock responses."""
    return CommonApiMocks()


def with_mock_http_server(*routes: tuple[str, str, Any]) -> Any:
    """Decorator to automatically set up mock HTTP server with predefined routes.

    Args:
        routes: Tuples of (method, url, response_data)

    Example:
        @with_mock_http_server(
            ("GET", "https://api.example.com/data", {"key": "value"}),
            ("POST", "https://api.example.com/submit", {"success": True})
        )
        def test_my_function():
            # Test code here
            pass
    """

    def decorator(func: Any) -> Any:
        import asyncio
        from functools import wraps

        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with respx.mock:
                    for method, url, response_data in routes:
                        if isinstance(response_data, str):
                            content = response_data
                            content_type = "text/plain"
                        else:
                            content = json.dumps(response_data)
                            content_type = "application/json"

                        if method.upper() == "GET":
                            respx.get(url).mock(
                                return_value=Response(
                                    200,
                                    headers={"Content-Type": content_type},
                                    content=content,
                                )
                            )
                        elif method.upper() == "POST":
                            respx.post(url).mock(
                                return_value=Response(
                                    200,
                                    headers={"Content-Type": content_type},
                                    content=content,
                                )
                            )

                    return await func(*args, **kwargs)

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with respx.mock:
                    for method, url, response_data in routes:
                        if isinstance(response_data, str):
                            content = response_data
                            content_type = "text/plain"
                        else:
                            content = json.dumps(response_data)
                            content_type = "application/json"

                        if method.upper() == "GET":
                            respx.get(url).mock(
                                return_value=Response(
                                    200,
                                    headers={"Content-Type": content_type},
                                    content=content,
                                )
                            )
                        elif method.upper() == "POST":
                            respx.post(url).mock(
                                return_value=Response(
                                    200,
                                    headers={"Content-Type": content_type},
                                    content=content,
                                )
                            )

                    return func(*args, **kwargs)

            return sync_wrapper

    return decorator


@pytest.fixture
def mock_external_apis(
    mock_http_server: MockHttpServer, common_api_mocks: CommonApiMocks
) -> MockHttpServer:
    """Pre-configure mock server with common external APIs."""
    # Add common external API endpoints
    mock_http_server.add_route(
        "GET", "https://httpbin.org/json", response_data=common_api_mocks.httpbin_json()
    )

    mock_http_server.add_route(
        "GET",
        "https://httpbin.org/robots.txt",
        text=common_api_mocks.httpbin_robots_txt(),
    )

    # Add UniProt endpoints
    mock_http_server.add_route(
        "GET",
        "https://rest.uniprot.org/uniprotkb/P0DTC2.fasta",
        text=common_api_mocks.uniprot_fasta("P0DTC2"),
    )

    mock_http_server.add_route(
        "GET",
        "https://rest.uniprot.org/uniprotkb/search*",
        response_data=common_api_mocks.uniprot_json("P0DTC2"),
    )

    # Add PDB endpoints
    mock_http_server.add_route(
        "GET",
        "https://data.rcsb.org/rest/v1/core/entry/*",
        response_data=common_api_mocks.pdb_json("6VSB"),
    )

    mock_http_server.start()
    return mock_http_server
