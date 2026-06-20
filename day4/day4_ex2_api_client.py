import logging
import time
import json

from typing import Any, Callable, TypeVar
from functools import wraps

log = logging.getLogger(__name__)
T = TypeVar("T")


class FDEBaseError(Exception):
    """Base for all TechStar FDE pipeline errors."""

    def __init__(self, message: str, context: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        if self.context:
            ctx = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            return f"{self.message} | {ctx}"
        return self.message


class APIClientError(FDEBaseError):
    """HTTP error from an external API call."""

    def __init__(self, url: str, status_code: int, message: str) -> None:
        super().__init__(
            f"HTTP {status_code}: {message}",
            context={"url": url, "status_code": status_code},
        )
        self.status_code = status_code
        self.url = url


class RateLimitError(APIClientError):
    """HTTP 429: API rate limit exceeded."""

    def __init__(self, url: str, retry_after: int = 60) -> None:
        super().__init__(url, 429, f"Rate limited — retry after {retry_after}s")
        self.retry_after = retry_after


class DataParseError(FDEBaseError):
    """Response body could not be parsed as expected schema."""

    def __init__(self, url: str, raw_response: str, reason: str) -> None:
        super().__init__(
            f"Parse error: {reason}",
            context={"url": url, "response_preview": raw_response[:100]},
        )


def retry(
    max_attempts: int = 3,
    backoff: float = 2.0,
    retriable_exceptions: tuple = (ConnectionError, TimeoutError, APIClientError),
) -> Callable:
    """
    Decorator: retry the wrapped function up to max_attempts times.
    Wait backoff^attempt seconds between retries (exponential backoff).
    Only retries on retriable_exceptions.
    Raises the last exception if all attempts fail.
    Does NOT retry on RateLimitError — caller should handle that separately.
    """

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except RateLimitError as e:
                    log.warning("Rate limited: %s", e)
                    raise
                except retriable_exceptions as e:
                    last_exc = e
                    wait = backoff**attempt
                    log.warning(
                        "Attempt %d/%d failed: %s. Retrying in %.1fs",
                        attempt,
                        max_attempts,
                        e,
                        wait,
                    )
                    if attempt < max_attempts:
                        time.sleep(wait)

            log.error("All %d attempts exhausted", max_attempts)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator


class CarrierAPIClient:
    """
    HTTP client for the carrier tracking API.
    Supports context manager usage:
        with CarrierAPIClient(base_url, api_key) as client:
            data = client.get_shipments('2024-01-20')
    """

    BASE_TIMEOUT = 30
    _call_count: int = 0

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._session_open = False
        self._request_count = 0

    def __enter__(self) -> "CarrierAPIClient":
        self._session_open = True
        log.info("CarrierAPIClient session opened: %s", self.base_url)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._session_open = False
        log.info(
            "CarrierAPIClient session closed. Requests made: %d", self._request_count
        )
        if exc_type is not None:
            log.error("Session closed due to exception: %s", exc_val)

    def _check_session(self) -> None:
        if not self._session_open:
            raise RuntimeError("CarrierAPIClient must be used as a context manager")

    def _parse_response(self, url: str, body: str) -> dict:
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise DataParseError(url, body, str(e)) from e

    def _handle_status(self, url: str, status_code: int, body: str) -> dict:
        if status_code == 200:
            return self._parse_response(url, body)

        if status_code == 429:
            retry_after = 60
            try:
                retry_after = json.loads(body).get("retry_after", 60)
            except (json.JSONDecodeError, AttributeError):
                pass
            raise RateLimitError(url, retry_after)

        if 500 <= status_code < 600:
            raise APIClientError(url, status_code, "Server error")

        if 400 <= status_code < 500:
            raise APIClientError(url, status_code, "Client error")

        raise APIClientError(url, status_code, "Unexpected status code")

    @retry(
        max_attempts=3,
        backoff=2.0,
        retriable_exceptions=(ConnectionError, TimeoutError, APIClientError),
    )
    def get_shipments(self, date: str) -> list[dict]:
        self._check_session()
        url = f"{self.base_url}/v1/shipments?date={date}"
        self._request_count += 1
        log.debug("GET %s", url)

        status_code, body = self._simulate_http(url)
        return self._handle_status(url, status_code, body).get("shipments", [])

    def _simulate_http(self, url: str) -> tuple[int, str]:
        CarrierAPIClient._call_count += 1
        if CarrierAPIClient._call_count <= 2:
            raise ConnectionError(
                f"Simulated network failure #{CarrierAPIClient._call_count}"
            )
        return 200, json.dumps(
            {
                "shipments": [
                    {
                        "id": "SH-001",
                        "carrier": "DHL",
                        "status": "in_transit",
                        "delay": 2,
                    },
                    {
                        "id": "SH-002",
                        "carrier": "FedEx",
                        "status": "delivered",
                        "delay": 0,
                    },
                ]
            }
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    with CarrierAPIClient(
        base_url="https://api.carrier-platform.in",
        api_key="secret-key-123",
    ) as client:
        shipments = client.get_shipments("2024-01-20")
        print(f"Retrieved {len(shipments)} shipments:")
        for s in shipments:
            print(" ", s)

        try:
            client.get_shipments("2024-01-20")
        except RuntimeError as e:
            print(f"Expected RuntimeError: {e}")

        try:
            client._session_open = True
            client._parse_response("http://test", "not valid json {{")
        except DataParseError as e:
            print(f"Expected DataParseError: {e}")
        finally:
            client._session_open = False
