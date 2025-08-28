"""HTTP client utilities for API requests."""
from typing import Any, Optional
import httpx
from .constants import USER_AGENT


async def make_api_request(
    url: str,
    headers: Optional[dict] = None,
    timeout: float = 30.0,
    accept_format: str = "application/json"
) -> Optional[Any]:
    """Make an HTTP request with proper error handling.
    
    Args:
        url: The URL to request
        headers: Optional custom headers
        timeout: Request timeout in seconds
        accept_format: Accept header format
        
    Returns:
        Response data (text or JSON) or None if failed
    """
    default_headers = {
        "User-Agent": USER_AGENT,
        "Accept": accept_format
    }
    
    if headers:
        default_headers.update(headers)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=default_headers, timeout=timeout)
            response.raise_for_status()
            
            if accept_format == "text/plain":
                return response.text
            else:
                return response.json()
                
        except Exception:
            return None


async def make_fasta_request(url: str) -> Optional[str]:
    """Make a request specifically for FASTA data.
    
    Args:
        url: The URL to request FASTA data from
        
    Returns:
        FASTA text or None if failed
    """
    return await make_api_request(url, accept_format="text/plain")