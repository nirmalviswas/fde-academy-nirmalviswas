from __future__ import annotations
import time
import logging
import json
from typing import Any, Callable, TypeVar
from functools import wraps

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)
T = TypeVar("T")


# ============================================================
# TASK 1A: Custom exceptions
# ============================================================


class APIClientError(Exception):
    """Base error for API client failures, carries HTTP context."""

    def __init__(self, status_code: int, message: str, url: str) -> None:
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.url = url


class RateLimitError(APIClientError):
    """Raised on HTTP 429 — caller should wait retry_after seconds."""

    def __init__(self, url: str, retry_after: int) -> None:
        super().__init__(429, f"Rate limited, retry after {retry_after}s", url)
        self.retry_after = retry_after


# PROVIDED: simulated unreliable transport — do not modify
_call_log: list[int] = []


def mock_http_get(url: str, headers: dict) -> tuple[int, str]:
    """
    Simulates an unreliable API:
    - Missing/wrong API key -> 401
    - First call -> 500 (simulated transient failure)
    - Second call -> 429 rate limited (retry_after=1)
    - Third call onward -> 200 success
    """
    if headers.get("X-API-Key") != "valid-test-key-123":
        return 401, json.dumps({"error": "Invalid API key"})

    _call_log.append(1)
    attempt_number = len(_call_log)

    if attempt_number == 1:
        return 500, json.dumps({"error": "Internal server error"})
    elif attempt_number == 2:
        return 429, json.dumps({"error": "Rate limited", "retry_after": 1})
    else:
        shipment_id = url.rstrip("/").split("/")[-1]
        return 200, json.dumps(
            {
                "shipment_id": shipment_id,
                "carrier": "DHL",
                "status": "in_transit",
                "delay_days": 1,
            }
        )


# ============================================================
# TASK 2: Retry decorator
# ============================================================


def with_retry(max_attempts: int = 4, backoff_base: float = 2.0) -> Callable:
    """
    Decorator: retry on APIClientError with status >= 500,
    using exponential backoff (backoff_base ** attempt seconds).
    On RateLimitError: sleep for exactly e.retry_after seconds, then retry.
    Does NOT retry on 4xx errors other than 429.
    Raises the last exception if max_attempts is exhausted.
    """

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except RateLimitError as e:
                    log.warning(
                        "Rate limited. Waiting %ds before retry.", e.retry_after
                    )
                    time.sleep(e.retry_after)
                    last_exc = e
                except APIClientError as e:
                    if e.status_code < 500:
                        raise  # 4xx (non-429) — do not retry
                    wait = backoff_base**attempt
                    log.warning(
                        "Server error %d. Retrying in %.1fs (attempt %d/%d)",
                        e.status_code,
                        wait,
                        attempt,
                        max_attempts,
                    )
                    time.sleep(wait)
                    last_exc = e
            log.error("All %d attempts exhausted", max_attempts)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator


# ============================================================
# TASK 3: LogisticsAPIClient class
# ============================================================


class LogisticsAPIClient:
    """Authenticated, resilient client for the logistics carrier API."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._headers = {"X-API-Key": api_key}

    def _handle_response(self, url: str, status: int, body: str) -> dict:
        """
        Route an HTTP status to the right outcome.
        200 -> parse and return JSON body as dict
        429 -> raise RateLimitError (parse retry_after from body)
        401/403 -> raise APIClientError (not retriable)
        5xx -> raise APIClientError (retriable by the decorator)
        """
        parsed = json.loads(body)

        if status == 200:
            return parsed
        elif status == 429:
            retry_after = parsed.get("retry_after", 60)
            raise RateLimitError(url, retry_after)
        elif status in (401, 403):
            raise APIClientError(status, parsed.get("error", "Forbidden"), url)
        elif status >= 500:
            raise APIClientError(status, parsed.get("error", "Server error"), url)
        else:
            raise APIClientError(status, parsed.get("error", "Unexpected error"), url)

    @with_retry(max_attempts=4, backoff_base=2.0)
    def get_shipment(self, shipment_id: str) -> dict:
        """Fetch a shipment record, retrying automatically on transient failures."""
        url = f"{self.base_url}/v1/shipments/{shipment_id}"
        status, body = mock_http_get(url, self._headers)
        return self._handle_response(url, status, body)


# ============================================================
# TASK 4: Test script
# ============================================================

if __name__ == "__main__":  # pragma: no cover
    client = LogisticsAPIClient(
        base_url="https://api.carrier-platform.in",
        api_key="valid-test-key-123",
    )

    print("=== Fetching SH-001 (will hit 500, then 429, then succeed) ===")
    result = client.get_shipment("SH-001")
    print(f"Final result: {result}")
    print()

    print("=== Testing invalid API key ===")
    bad_client = LogisticsAPIClient(
        base_url="https://api.carrier-platform.in",
        api_key="wrong-key",
    )
    try:
        bad_client.get_shipment("SH-002")
    except APIClientError as e:
        print(f"Expected failure (not retried): {e}")
