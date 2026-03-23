"""CueAPI client — the main entry point for the SDK."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from cueapi.exceptions import (
    AuthenticationError,
    CueAPIError,
    CueAPIServerError,
    CueLimitExceededError,
    CueNotFoundError,
    InvalidScheduleError,
    RateLimitError,
)
from cueapi.resources.cues import CuesResource
from cueapi.resources.executions import ExecutionsResource

DEFAULT_BASE_URL = "https://api.cueapi.ai"
DEFAULT_TIMEOUT = 30.0


class CueAPI:
    """CueAPI client.

    Usage::

        from cueapi import CueAPI

        client = CueAPI("cue_sk_your_key")
        cue = client.cues.create(
            name="daily-report",
            cron="0 9 * * *",
            callback="https://my-app.com/webhook",
        )
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the CueAPI client.

        Args:
            api_key: Your CueAPI API key (starts with ``cue_sk_``).
            base_url: API base URL (default ``https://api.cueapi.ai``).
            timeout: Request timeout in seconds (default 30).
        """
        if not api_key:
            raise ValueError("api_key is required")

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "cueapi-python/0.1.0",
            },
            timeout=timeout,
        )

        # Resources
        self.cues = CuesResource(self)
        self.executions = ExecutionsResource(self)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()

    def __enter__(self) -> CueAPI:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # --- HTTP helpers ---

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make an HTTP request and handle errors."""
        response = self._http.request(method, path, json=json, params=params)
        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> Any:
        """Parse response, raise typed exceptions on errors."""
        if response.status_code == 204:
            return None

        try:
            data = response.json()
        except Exception:
            data = {"error": {"message": response.text, "code": "unknown"}}

        if response.is_success:
            return data

        # Extract error info
        error_body = data.get("error", data)
        message = error_body.get("message", "Unknown error")
        code = error_body.get("code", "unknown")
        status = response.status_code

        kwargs = dict(
            message=message,
            status_code=status,
            code=code,
            body=data,
        )

        if status == 401:
            raise AuthenticationError(**kwargs)
        elif status == 403:
            raise CueLimitExceededError(**kwargs)
        elif status == 404:
            raise CueNotFoundError(**kwargs)
        elif status == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                retry_after=int(retry_after) if retry_after else None,
                **kwargs,
            )
        elif status == 400 or status == 422:
            raise InvalidScheduleError(**kwargs)
        elif status >= 500:
            raise CueAPIServerError(**kwargs)
        else:
            raise CueAPIError(**kwargs)

    def _get(self, path: str, **kwargs: Any) -> Any:
        return self._request("GET", path, **kwargs)

    def _post(self, path: str, **kwargs: Any) -> Any:
        return self._request("POST", path, **kwargs)

    def _patch(self, path: str, **kwargs: Any) -> Any:
        return self._request("PATCH", path, **kwargs)

    def _delete(self, path: str, **kwargs: Any) -> Any:
        return self._request("DELETE", path, **kwargs)
