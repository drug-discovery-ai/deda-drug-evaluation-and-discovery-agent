"""HTTP client utilities for API requests."""

from typing import Union

import httpx

from drug_discovery_agent.utils.constants import USER_AGENT


async def make_api_request(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
    accept_format: str = "application/json",
) -> Union[dict[str, object], str, None]:
    """Make an HTTP request with proper error handling.

    Args:
        url: The URL to request
        headers: Optional custom headers
        timeout: Request timeout in seconds
        accept_format: Accept header format

    Returns:
        Response data (text or JSON) or None if failed
    """
    default_headers = {"User-Agent": USER_AGENT, "Accept": accept_format}

    if headers:
        default_headers.update(headers)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=default_headers, timeout=timeout)
            response.raise_for_status()

            if accept_format == "text/plain":
                text_response: str = response.text
                return text_response
            else:
                json_data = response.json()
                # Ensure we return dict[str, object] or None as promised
                if isinstance(json_data, dict):
                    return json_data
                return None

        except Exception:
            return None


async def make_fasta_request(url: str) -> str | None:
    """Make a request specifically for FASTA data.

    Args:
        url: The URL to request FASTA data from

    Returns:
        FASTA text or None if failed
    """
    result = await make_api_request(url, accept_format="text/plain")
    # Since we specify text/plain, we should get str or None
    return result if isinstance(result, str) else None
