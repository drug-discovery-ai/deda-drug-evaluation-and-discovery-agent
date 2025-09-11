"""HTTP interceptor for unified snapshot testing system."""

import hashlib
import json
from abc import ABC, abstractmethod
from typing import Any
from unittest.mock import Mock

import httpx

from snapshots.manager import SnapshotManager

# Domain to service name mapping
DOMAIN_SERVICE_MAP = {
    "ebi.ac.uk": "ebi",
    "platform.opentargets.org": "opentargets",
    "uniprot.org": "uniprot",
    "rcsb.org": "pdb",
}


class HTTPBackend(ABC):
    """Abstract base for HTTP backends."""

    @abstractmethod
    async def handle_request(
        self, method: str, url: str, **kwargs: dict
    ) -> httpx.Response:
        """Handle HTTP request and return response."""
        pass


class SnapshotHTTPBackend(HTTPBackend):
    """Backend that uses saved snapshots."""

    def __init__(self) -> None:
        self.manager = SnapshotManager()

    def _generate_key(self, method: str, url: str, **kwargs: dict) -> str:
        """Generate snapshot key from request details."""
        # Special handling for EBI API to match existing snapshot format
        if "ebi.ac.uk" in str(url):
            params = kwargs.get("params", {})
            if "q" in params and "ontology" in params:
                # Match existing EBI snapshot key format: ebi_api_search_{query}_{ontology}_{hash}
                query = params["q"].replace(" ", "")
                ontology = params["ontology"]

                # Create deterministic hash for uniqueness
                key_data = {"method": method.upper(), "url": str(url), "params": params}
                key_string = json.dumps(key_data, sort_keys=True)
                key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]

                return f"ebi_api_search_{query}_{ontology}_{key_hash}"

        # Generic key generation for other services
        key_data = {
            "method": method.upper(),
            "url": str(url),
        }

        # Include relevant request parameters
        if "params" in kwargs:
            key_data["params"] = kwargs["params"]
        if "json" in kwargs:
            key_data["json"] = kwargs["json"]
        if "data" in kwargs:
            key_data["data"] = kwargs["data"]

        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()[:12]

        # Extract service from URL for better organization
        service = _get_service_from_url(url)

        return f"{service}_api_{method.lower()}_{key_hash}"

    async def handle_request(
        self, method: str, url: str, **kwargs: dict
    ) -> httpx.Response:
        """Return response from snapshot."""
        key = self._generate_key(method, url, **kwargs)
        snapshot_data = self.manager.load_snapshot(key)

        if snapshot_data is None:
            # Return empty response if no snapshot found
            mock_response = Mock(spec=httpx.Response)
            mock_response.status_code = 200
            mock_response.json.return_value = {}
            mock_response.text = "{}"
            mock_response.headers = {"content-type": "application/json"}
            mock_response.is_success = True
            return mock_response

        # Create response from snapshot data
        mock_response = Mock(spec=httpx.Response)
        # Note: snapshot_data has nested structure with metadata
        metadata = snapshot_data.get("metadata", {})
        mock_response.status_code = metadata.get("status_code", 200)

        response_body = snapshot_data.get("response", {})
        if isinstance(response_body, dict):
            mock_response.json.return_value = response_body
            mock_response.text = json.dumps(response_body)
        else:
            mock_response.text = str(response_body)
            mock_response.json.side_effect = json.JSONDecodeError("Not JSON", "", 0)

        mock_response.headers = metadata.get(
            "headers", {"content-type": "application/json"}
        )
        mock_response.is_success = 200 <= mock_response.status_code < 300

        # Make raise_for_status() work correctly for error responses
        def raise_for_status() -> None:
            if not mock_response.is_success:
                # Create proper HTTP error
                import httpx

                raise httpx.HTTPStatusError(
                    f"HTTP {mock_response.status_code}",
                    request=Mock(),
                    response=mock_response,
                )

        mock_response.raise_for_status = raise_for_status

        return mock_response


class SnapshotRecordingBackend(HTTPBackend):
    """Backend that records real API responses as snapshots."""

    def __init__(self, original_request: Any = None) -> None:
        self.manager = SnapshotManager()
        # Store the original request method to avoid recursive interception
        self._original_request = original_request

    def _generate_key(self, method: str, url: str, **kwargs: dict) -> str:
        """Generate snapshot key from request details."""
        # Special handling for EBI API to match existing snapshot format
        if "ebi.ac.uk" in str(url):
            params = kwargs.get("params", {})
            if "q" in params and "ontology" in params:
                # Match existing EBI snapshot key format: ebi_api_search_{query}_{ontology}_{hash}
                query = params["q"].replace(" ", "")
                ontology = params["ontology"]

                # Create deterministic hash for uniqueness
                key_data = {"method": method.upper(), "url": str(url), "params": params}
                key_string = json.dumps(key_data, sort_keys=True)
                key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]

                return f"ebi_api_search_{query}_{ontology}_{key_hash}"

        # Generic key generation for other services
        key_data = {
            "method": method.upper(),
            "url": str(url),
        }

        if "params" in kwargs:
            key_data["params"] = kwargs["params"]
        if "json" in kwargs:
            key_data["json"] = kwargs["json"]
        if "data" in kwargs:
            key_data["data"] = kwargs["data"]

        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()[:12]

        service = _get_service_from_url(url)

        return f"{service}_api_{method.lower()}_{key_hash}"

    async def handle_request(
        self, method: str, url: str, **kwargs: dict
    ) -> httpx.Response:
        """Make real request and save response as snapshot."""
        try:
            # Make real HTTP request using original unpatched method
            if self._original_request is None:
                raise RuntimeError(
                    "No original request method available - cannot make real requests"
                )

            async with httpx.AsyncClient() as client:
                # Use the original request method - it expects self as first argument
                response = await self._original_request(client, method, url, **kwargs)

            # Prepare snapshot data
            snapshot_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "request": {
                    "method": method,
                    "url": str(url),
                    "params": kwargs.get("params"),
                    "json": kwargs.get("json"),
                    "data": kwargs.get("data"),
                },
            }

            # Handle response body based on content type
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    snapshot_data["response"] = response.json()
                except:  # noqa: E722
                    snapshot_data["response"] = response.text
            else:
                snapshot_data["response"] = response.text

            # Save snapshot
            key = self._generate_key(method, url, **kwargs)

            # Create metadata for the snapshot
            metadata = {
                "url": str(url),
                "method": method.upper(),
                "status_code": response.status_code,
                "content_type": response.headers.get(
                    "content-type", "application/json"
                ),
            }

            # Add request parameters to metadata
            if "params" in kwargs:
                metadata["request_params"] = kwargs["params"]
            if "json" in kwargs:
                metadata["request_json"] = kwargs["json"]

            self.manager.save_snapshot(key, snapshot_data["response"], metadata)
            return response  # type: ignore[no-any-return]

        except Exception as e:
            # On error, create error response snapshot
            error_data = {
                "status_code": getattr(e, "status_code", 500),
                "headers": {"content-type": "application/json"},
                "response": {"error": str(e)},
                "request": {
                    "method": method,
                    "url": str(url),
                },
            }

            key = self._generate_key(method, url, **kwargs)
            metadata = {
                "url": str(url),
                "method": method.upper(),
                "status_code": getattr(e, "status_code", 500),
                "content_type": "application/json",
            }
            self.manager.save_snapshot(key, error_data, metadata)

            # Re-raise the exception
            raise


class SnapshotValidationBackend(HTTPBackend):
    """Backend that validates existing snapshots against live API."""

    def __init__(self, original_request: Any = None) -> None:
        self.manager = SnapshotManager()
        self.validation_results: list[dict[str, Any]] = []
        # Store the original request method to avoid recursive interception
        self._original_request = original_request

    def _generate_key(self, method: str, url: str, **kwargs: dict) -> str:
        """Generate snapshot key from request details."""
        # Special handling for EBI API to match existing snapshot format
        if "ebi.ac.uk" in str(url):
            params = kwargs.get("params", {})
            if "q" in params and "ontology" in params:
                # Match existing EBI snapshot key format: ebi_api_search_{query}_{ontology}_{hash}
                query = params["q"].replace(" ", "")
                ontology = params["ontology"]

                # Create deterministic hash for uniqueness
                key_data = {"method": method.upper(), "url": str(url), "params": params}
                key_string = json.dumps(key_data, sort_keys=True)
                key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]

                return f"ebi_api_search_{query}_{ontology}_{key_hash}"

        # Generic key generation for other services
        key_data = {
            "method": method.upper(),
            "url": str(url),
        }

        if "params" in kwargs:
            key_data["params"] = kwargs["params"]
        if "json" in kwargs:
            key_data["json"] = kwargs["json"]
        if "data" in kwargs:
            key_data["data"] = kwargs["data"]

        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()[:12]

        service = _get_service_from_url(url)

        return f"{service}_api_{method.lower()}_{key_hash}"

    async def handle_request(
        self, method: str, url: str, **kwargs: dict
    ) -> httpx.Response:
        """Validate snapshot against live API response."""
        key = self._generate_key(method, url, **kwargs)
        snapshot_data = self.manager.load_snapshot(key)

        if snapshot_data is None:
            self.validation_results.append(
                {
                    "key": key,
                    "status": "missing_snapshot",
                    "message": f"No snapshot found for {method} {url}",
                }
            )
            # Return empty mock response
            mock_response = Mock(spec=httpx.Response)
            mock_response.status_code = 200
            mock_response.json.return_value = {}
            mock_response.text = "{}"
            mock_response.headers = {"content-type": "application/json"}
            mock_response.is_success = True
            return mock_response

        try:
            # Make real HTTP request using original unpatched method
            if self._original_request is None:
                raise RuntimeError(
                    "No original request method available - cannot make real requests"
                )

            # Create a fresh client and use the original request method
            async with httpx.AsyncClient() as client:
                # Use the original request method - it expects self as first argument
                real_response = await self._original_request(
                    client, method, url, **kwargs
                )

            # Compare responses
            matches = True
            issues = []
            metadata = snapshot_data.get("metadata", {})

            if real_response.status_code != metadata.get("status_code"):
                matches = False
                issues.append(
                    f"Status code mismatch: {real_response.status_code} vs {metadata.get('status_code')}"
                )

            # Compare response bodies (simplified comparison)
            content_type = real_response.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    real_json = real_response.json()
                    snapshot_response = snapshot_data.get("response", {})
                    if real_json != snapshot_response:
                        matches = False
                        issues.append("Response body differs from snapshot")
                except:  # noqa: E722
                    pass

            self.validation_results.append(
                {
                    "key": key,
                    "status": "valid" if matches else "mismatch",
                    "issues": issues,
                    "url": str(url),
                }
            )

            # Return the snapshot data (not real response) for consistent test behavior
            mock_response = Mock(spec=httpx.Response)
            metadata = snapshot_data.get("metadata", {})
            mock_response.status_code = metadata.get("status_code", 200)

            response_body = snapshot_data.get("response", {})
            if isinstance(response_body, dict):
                mock_response.json.return_value = response_body
                mock_response.text = json.dumps(response_body)
            else:
                mock_response.text = str(response_body)
                mock_response.json.side_effect = json.JSONDecodeError("Not JSON", "", 0)

            mock_response.headers = metadata.get(
                "headers", {"content-type": "application/json"}
            )
            mock_response.is_success = 200 <= mock_response.status_code < 300

            # Make raise_for_status() work correctly
            def raise_for_status() -> None:
                if not mock_response.is_success:
                    import httpx

                    raise httpx.HTTPStatusError(
                        f"HTTP {mock_response.status_code}",
                        request=Mock(),
                        response=mock_response,
                    )

            mock_response.raise_for_status = raise_for_status

            return mock_response

        except Exception as e:
            self.validation_results.append(
                {
                    "key": key,
                    "status": "error",
                    "message": f"Error validating snapshot: {str(e)}",
                    "url": str(url),
                }
            )

            # Return snapshot data even if validation failed
            mock_response = Mock(spec=httpx.Response)
            error_metadata = snapshot_data.get("metadata", {})
            mock_response.status_code = error_metadata.get("status_code", 200)

            response_body = snapshot_data.get("response", {})
            if isinstance(response_body, dict):
                mock_response.json.return_value = response_body
                mock_response.text = json.dumps(response_body)
            else:
                mock_response.text = str(response_body)
                mock_response.json.side_effect = json.JSONDecodeError("Not JSON", "", 0)

            mock_response.headers = error_metadata.get(
                "headers", {"content-type": "application/json"}
            )
            mock_response.is_success = 200 <= mock_response.status_code < 300

            # Make raise_for_status() work correctly for error responses
            def raise_for_status() -> None:
                if not mock_response.is_success:
                    # Create proper HTTP error
                    import httpx

                    raise httpx.HTTPStatusError(
                        f"HTTP {mock_response.status_code}",
                        request=Mock(),
                        response=mock_response,
                    )

            mock_response.raise_for_status = raise_for_status

            return mock_response


class HTTPInterceptor:
    """Main HTTP interceptor that patches httpx.AsyncClient."""

    def __init__(self, backend: HTTPBackend):
        self.backend = backend
        self.original_request = None
        # Pass original request to recording backend if needed
        if hasattr(backend, "_original_request"):
            backend._original_request = None  # Will be set in __enter__

    def __enter__(self) -> "HTTPInterceptor":
        """Start intercepting HTTP requests."""
        self.original_request = httpx.AsyncClient.request  # type: ignore[assignment]
        # Pass original request to recording backend if needed
        if hasattr(self.backend, "_original_request"):
            self.backend._original_request = self.original_request

        # Create intercepted method that handles the self parameter properly
        async def intercepted_request(
            client_instance: Any, method: str, url: Any, **kwargs: Any
        ) -> httpx.Response:
            """Intercepted request method."""
            return await self.backend.handle_request(method, str(url), **kwargs)

        httpx.AsyncClient.request = intercepted_request  # type: ignore[method-assign,assignment]
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stop intercepting HTTP requests."""
        if self.original_request:
            httpx.AsyncClient.request = self.original_request


def _get_service_from_url(url: str) -> str:
    """Extract service name from URL using domain mapping."""
    url_str = str(url)
    for domain, service in DOMAIN_SERVICE_MAP.items():
        if domain in url_str:
            return service
    return "misc"
