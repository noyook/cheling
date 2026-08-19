"""Unified async HTTP client using httpx.AsyncClient"""
import logging
from typing import Optional, Dict, Any

import httpx

from packages.waybill_sync.core.exceptions import APIError

logger = logging.getLogger(__name__)


class HttpClient:
    """Singleton async HTTP client with connection pooling."""

    _instance: Optional[httpx.AsyncClient] = None

    @classmethod
    def get_client(
        cls,
        verify: bool = False,
        timeout: float = 30.0,
    ) -> httpx.AsyncClient:
        """Get or create the AsyncClient instance."""
        if cls._instance is None or cls._instance.is_closed:
            cls._instance = httpx.AsyncClient(
                verify=verify,
                timeout=httpx.Timeout(timeout),
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en,zh-CN;q=0.9,zh;q=0.8",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/147.0.0.0 Safari/537.36",
                },
            )
        return cls._instance

    @classmethod
    async def close(cls):
        """Close the client and release connections."""
        if cls._instance and not cls._instance.is_closed:
            await cls._instance.aclose()
            cls._instance = None
            logger.info("HTTP client closed")


async def request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    verify: bool = False,
    timeout: float = 30.0,
) -> httpx.Response:
    """Make an HTTP request with unified error handling.

    Args:
        method: HTTP method (GET, POST, etc.)
        url: Full URL
        headers: Optional headers dict
        params: Optional query params
        json_body: Optional JSON body (for POST/PUT)
        verify: SSL verification
        timeout: Request timeout in seconds

    Returns:
        httpx.Response

    Raises:
        APIError: On HTTP error or request failure
    """
    client = HttpClient.get_client(verify=verify, timeout=timeout)
    try:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_body,
        )
        response.raise_for_status()
        return response
    except httpx.TimeoutException:
        raise APIError(f"Request timeout: {method} {url}")
    except httpx.HTTPStatusError as e:
        raise APIError(f"HTTP {e.response.status_code}: {e.response.text}")
    except httpx.HTTPError as e:
        raise APIError(f"HTTP request failed: {e}")
