from __future__ import annotations

import contextlib
import logging
import random
import time

import httpx

from tubescrape._innertube import InnerTube
from tubescrape.exceptions import ProxyBlockedError, RateLimitError, RequestError

logger = logging.getLogger('tubescrape.http')


class HTTPClient:
    """HTTP transport layer with retry, proxy support, and cookie management.

    Supports both synchronous and asynchronous operations via httpx.

    Args:
        proxy: Single proxy URL (e.g. 'http://user:pass@host:port').
        proxies: List of proxy URLs for rotation.
        timeout: Request timeout in seconds.
        max_retries: Maximum retry attempts on transient failures.
        cookies: Additional cookies to include in requests.
        transcript_proxy: Single proxy URL for transcript requests (residential recommended).
        transcript_proxies: List of proxy URLs for transcript rotation.
    """

    RETRYABLE_STATUS_CODES: tuple[int, ...] = (429, 500, 502, 503, 504)

    def __init__(
        self,
        proxy: str | None = None,
        proxies: list[str] | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        cookies: dict[str, str] | None = None,
        transcript_proxy: str | None = None,
        transcript_proxies: list[str] | None = None,
    ):
        self._proxy = proxy
        self._proxies = proxies or []
        self._proxy_index = 0
        self._timeout = timeout
        self._max_retries = max_retries
        self._cookies = {**InnerTube.VISITOR_COOKIES, **(cookies or {})}

        # Separate proxy pool for transcripts (player + captions endpoints)
        self._transcript_proxy = transcript_proxy
        self._transcript_proxies = transcript_proxies or []
        self._transcript_proxy_index = 0

        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None

    @property
    def _current_proxy(self) -> str | None:
        if self._proxy:
            return self._proxy
        if self._proxies:
            proxy = self._proxies[self._proxy_index % len(self._proxies)]
            self._proxy_index += 1
            return proxy
        return None

    @property
    def _current_transcript_proxy(self) -> str | None:
        if self._transcript_proxy:
            return self._transcript_proxy
        if self._transcript_proxies:
            proxy = self._transcript_proxies[
                self._transcript_proxy_index % len(self._transcript_proxies)
            ]
            self._transcript_proxy_index += 1
            return proxy
        return self._current_proxy

    @property
    def has_transcript_proxies(self) -> bool:
        return bool(self._transcript_proxy or self._transcript_proxies)

    def _get_sync_client(self) -> httpx.Client:
        if self._sync_client is None or self._sync_client.is_closed:
            proxy = self._current_proxy
            self._sync_client = httpx.Client(
                headers=InnerTube.DEFAULT_HEADERS,
                cookies=self._cookies,
                timeout=self._timeout,
                proxy=proxy,
                follow_redirects=True,
            )
        return self._sync_client

    def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None or self._async_client.is_closed:
            proxy = self._current_proxy
            self._async_client = httpx.AsyncClient(
                headers=InnerTube.DEFAULT_HEADERS,
                cookies=self._cookies,
                timeout=self._timeout,
                proxy=proxy,
                follow_redirects=True,
            )
        return self._async_client

    def _handle_response(self, response: httpx.Response) -> httpx.Response:
        """Check response status and raise appropriate exceptions."""
        if response.status_code == 429:
            raise RateLimitError()
        if response.status_code == 403:
            body = response.text[:500]
            if any(sig in body for sig in ProxyBlockedError.FIREWALL_SIGNATURES):
                raise ProxyBlockedError()
            raise RequestError(
                'HTTP 403: %s' % body[:200],
                status_code=403,
            )
        if response.status_code in self.RETRYABLE_STATUS_CODES:
            raise RequestError(
                'HTTP %d (retryable)' % response.status_code,
                status_code=response.status_code,
            )
        if response.status_code >= 400:
            raise RequestError(
                'HTTP %d: %s' % (response.status_code, response.text[:200]),
                status_code=response.status_code,
            )
        return response

    @staticmethod
    def _backoff_delay(attempt: int) -> float:
        """Exponential backoff with jitter."""
        base = min(2 ** attempt, 30)
        jitter = random.uniform(0, base * 0.5)
        return base + jitter

    def post(self, url: str, json: dict, **kwargs) -> httpx.Response:
        """Send a POST request with retry logic.

        Args:
            url: Full URL to POST to.
            json: JSON payload.
            **kwargs: Additional arguments passed to httpx.Client.post.
        """
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                client = self._get_sync_client()
                response = client.post(url, json=json, **kwargs)
                return self._handle_response(response)
            except (RateLimitError, ProxyBlockedError) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    delay = self._backoff_delay(attempt)
                    logger.warning(
                        '%s (attempt %d/%d), retrying in %.1fs',
                        type(exc).__name__, attempt + 1,
                        self._max_retries + 1, delay,
                    )
                    time.sleep(delay)
                    self._rotate_proxy()
                    continue
            except RequestError as exc:
                if exc.status_code and exc.status_code in self.RETRYABLE_STATUS_CODES:
                    last_error = exc
                    if attempt < self._max_retries:
                        delay = self._backoff_delay(attempt)
                        logger.warning(
                            'Server error %d (attempt %d/%d), retrying in %.1fs',
                            exc.status_code, attempt + 1,
                            self._max_retries + 1, delay,
                        )
                        time.sleep(delay)
                        continue
                raise
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                self._reset_client_sync()
                if attempt < self._max_retries:
                    delay = self._backoff_delay(attempt)
                    logger.warning(
                        '%s (attempt %d/%d): %s, retrying in %.1fs',
                        type(exc).__name__, attempt + 1,
                        self._max_retries + 1, exc, delay,
                    )
                    time.sleep(delay)
                    self._rotate_proxy()

        raise RequestError(
            'Request failed after %d attempts: %s' % (self._max_retries + 1, last_error)
        )

    def get(self, url: str, **kwargs) -> httpx.Response:
        """Send a GET request with retry logic."""
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                client = self._get_sync_client()
                response = client.get(url, **kwargs)
                return self._handle_response(response)
            except (RateLimitError, ProxyBlockedError) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    delay = self._backoff_delay(attempt)
                    logger.warning(
                        '%s (attempt %d/%d), retrying in %.1fs',
                        type(exc).__name__, attempt + 1,
                        self._max_retries + 1, delay,
                    )
                    time.sleep(delay)
                    self._rotate_proxy()
                    continue
            except RequestError as exc:
                if exc.status_code and exc.status_code in self.RETRYABLE_STATUS_CODES:
                    last_error = exc
                    if attempt < self._max_retries:
                        delay = self._backoff_delay(attempt)
                        logger.warning(
                            'Server error %d (attempt %d/%d), retrying in %.1fs',
                            exc.status_code, attempt + 1,
                            self._max_retries + 1, delay,
                        )
                        time.sleep(delay)
                        continue
                raise
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                self._reset_client_sync()
                if attempt < self._max_retries:
                    delay = self._backoff_delay(attempt)
                    logger.warning(
                        '%s (attempt %d/%d): %s, retrying in %.1fs',
                        type(exc).__name__, attempt + 1,
                        self._max_retries + 1, exc, delay,
                    )
                    time.sleep(delay)
                    self._rotate_proxy()

        raise RequestError(
            'Request failed after %d attempts: %s' % (self._max_retries + 1, last_error)
        )

    async def apost(self, url: str, json: dict, **kwargs) -> httpx.Response:
        """Async POST request with retry logic."""
        import asyncio

        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                client = self._get_async_client()
                response = await client.post(url, json=json, **kwargs)
                return self._handle_response(response)
            except (RateLimitError, ProxyBlockedError) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    delay = self._backoff_delay(attempt)
                    logger.warning(
                        '%s (attempt %d/%d), retrying in %.1fs',
                        type(exc).__name__, attempt + 1,
                        self._max_retries + 1, delay,
                    )
                    await asyncio.sleep(delay)
                    self._rotate_proxy()
                    continue
            except RequestError as exc:
                if exc.status_code and exc.status_code in self.RETRYABLE_STATUS_CODES:
                    last_error = exc
                    if attempt < self._max_retries:
                        delay = self._backoff_delay(attempt)
                        logger.warning(
                            'Server error %d (attempt %d/%d), retrying in %.1fs',
                            exc.status_code, attempt + 1,
                            self._max_retries + 1, delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                raise
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                await self._reset_client_async()
                if attempt < self._max_retries:
                    delay = self._backoff_delay(attempt)
                    logger.warning(
                        '%s (attempt %d/%d): %s, retrying in %.1fs',
                        type(exc).__name__, attempt + 1,
                        self._max_retries + 1, exc, delay,
                    )
                    await asyncio.sleep(delay)
                    self._rotate_proxy()

        raise RequestError(
            'Request failed after %d attempts: %s' % (self._max_retries + 1, last_error)
        )

    async def aget(self, url: str, **kwargs) -> httpx.Response:
        """Async GET request with retry logic."""
        import asyncio

        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                client = self._get_async_client()
                response = await client.get(url, **kwargs)
                return self._handle_response(response)
            except (RateLimitError, ProxyBlockedError) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    delay = self._backoff_delay(attempt)
                    logger.warning(
                        '%s (attempt %d/%d), retrying in %.1fs',
                        type(exc).__name__, attempt + 1,
                        self._max_retries + 1, delay,
                    )
                    await asyncio.sleep(delay)
                    self._rotate_proxy()
                    continue
            except RequestError as exc:
                if exc.status_code and exc.status_code in self.RETRYABLE_STATUS_CODES:
                    last_error = exc
                    if attempt < self._max_retries:
                        delay = self._backoff_delay(attempt)
                        logger.warning(
                            'Server error %d (attempt %d/%d), retrying in %.1fs',
                            exc.status_code, attempt + 1,
                            self._max_retries + 1, delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                raise
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                await self._reset_client_async()
                if attempt < self._max_retries:
                    delay = self._backoff_delay(attempt)
                    logger.warning(
                        '%s (attempt %d/%d): %s, retrying in %.1fs',
                        type(exc).__name__, attempt + 1,
                        self._max_retries + 1, exc, delay,
                    )
                    await asyncio.sleep(delay)
                    self._rotate_proxy()

        raise RequestError(
            'Request failed after %d attempts: %s' % (self._max_retries + 1, last_error)
        )

    def _make_transcript_client_sync(self) -> httpx.Client:
        """Create a one-shot sync client using the transcript proxy pool."""
        proxy = self._current_transcript_proxy
        return httpx.Client(
            headers=InnerTube.DEFAULT_HEADERS,
            cookies=self._cookies,
            timeout=self._timeout,
            proxy=proxy,
            follow_redirects=True,
        )

    def _make_transcript_client_async(self) -> httpx.AsyncClient:
        """Create a one-shot async client using the transcript proxy pool."""
        proxy = self._current_transcript_proxy
        return httpx.AsyncClient(
            headers=InnerTube.DEFAULT_HEADERS,
            cookies=self._cookies,
            timeout=self._timeout,
            proxy=proxy,
            follow_redirects=True,
        )

    def transcript_post(self, url: str, json: dict, **kwargs) -> httpx.Response:
        """POST using transcript proxy pool. Falls back to normal post if no transcript proxies."""
        if not self.has_transcript_proxies:
            return self.post(url, json=json, **kwargs)

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            client = self._make_transcript_client_sync()
            try:
                response = client.post(url, json=json, **kwargs)
                return self._handle_response(response)
            except (RateLimitError, ProxyBlockedError) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    delay = self._backoff_delay(attempt)
                    logger.warning(
                        'Transcript %s (attempt %d/%d), rotating proxy',
                        type(exc).__name__, attempt + 1,
                        self._max_retries + 1,
                    )
                    time.sleep(delay)
                    continue
            except RequestError as exc:
                if exc.status_code and exc.status_code in self.RETRYABLE_STATUS_CODES:
                    last_error = exc
                    if attempt < self._max_retries:
                        time.sleep(self._backoff_delay(attempt))
                        continue
                raise
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    time.sleep(self._backoff_delay(attempt))
                    continue
            finally:
                client.close()

        raise RequestError(
            'Transcript request failed after %d attempts: %s'
            % (self._max_retries + 1, last_error)
        )

    def transcript_get(self, url: str, **kwargs) -> httpx.Response:
        """GET using transcript proxy pool. Falls back to normal get if no transcript proxies."""
        if not self.has_transcript_proxies:
            return self.get(url, **kwargs)

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            client = self._make_transcript_client_sync()
            try:
                response = client.get(url, **kwargs)
                return self._handle_response(response)
            except (RateLimitError, ProxyBlockedError) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    delay = self._backoff_delay(attempt)
                    logger.warning(
                        'Transcript %s (attempt %d/%d), rotating proxy',
                        type(exc).__name__, attempt + 1,
                        self._max_retries + 1,
                    )
                    time.sleep(delay)
                    continue
            except RequestError as exc:
                if exc.status_code and exc.status_code in self.RETRYABLE_STATUS_CODES:
                    last_error = exc
                    if attempt < self._max_retries:
                        time.sleep(self._backoff_delay(attempt))
                        continue
                raise
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    time.sleep(self._backoff_delay(attempt))
                    continue
            finally:
                client.close()

        raise RequestError(
            'Transcript request failed after %d attempts: %s'
            % (self._max_retries + 1, last_error)
        )

    async def transcript_apost(self, url: str, json: dict, **kwargs) -> httpx.Response:
        """Async POST using transcript proxy pool."""
        import asyncio

        if not self.has_transcript_proxies:
            return await self.apost(url, json=json, **kwargs)

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            client = self._make_transcript_client_async()
            try:
                response = await client.post(url, json=json, **kwargs)
                return self._handle_response(response)
            except (RateLimitError, ProxyBlockedError) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(self._backoff_delay(attempt))
                    continue
            except RequestError as exc:
                if exc.status_code and exc.status_code in self.RETRYABLE_STATUS_CODES:
                    last_error = exc
                    if attempt < self._max_retries:
                        await asyncio.sleep(self._backoff_delay(attempt))
                        continue
                raise
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(self._backoff_delay(attempt))
                    continue
            finally:
                await client.aclose()

        raise RequestError(
            'Transcript request failed after %d attempts: %s'
            % (self._max_retries + 1, last_error)
        )

    async def transcript_aget(self, url: str, **kwargs) -> httpx.Response:
        """Async GET using transcript proxy pool."""
        import asyncio

        if not self.has_transcript_proxies:
            return await self.aget(url, **kwargs)

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            client = self._make_transcript_client_async()
            try:
                response = await client.get(url, **kwargs)
                return self._handle_response(response)
            except (RateLimitError, ProxyBlockedError) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(self._backoff_delay(attempt))
                    continue
            except RequestError as exc:
                if exc.status_code and exc.status_code in self.RETRYABLE_STATUS_CODES:
                    last_error = exc
                    if attempt < self._max_retries:
                        await asyncio.sleep(self._backoff_delay(attempt))
                        continue
                raise
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(self._backoff_delay(attempt))
                    continue
            finally:
                await client.aclose()

        raise RequestError(
            'Transcript request failed after %d attempts: %s'
            % (self._max_retries + 1, last_error)
        )

    def _rotate_proxy(self) -> None:
        """Close current client to force a new proxy on next request."""
        if self._proxies:
            self.close_sync()

    def _reset_client_sync(self) -> None:
        """Reset sync client on network errors (stale connection, SSL, etc)."""
        if self._sync_client and not self._sync_client.is_closed:
            with contextlib.suppress(Exception):
                self._sync_client.close()
            self._sync_client = None
            logger.debug('Sync client reset due to network error')

    async def _reset_client_async(self) -> None:
        """Reset async client on network errors."""
        if self._async_client and not self._async_client.is_closed:
            with contextlib.suppress(Exception):
                await self._async_client.aclose()
            self._async_client = None
            logger.debug('Async client reset due to network error')

    def close_sync(self) -> None:
        """Close the synchronous HTTP client."""
        if self._sync_client and not self._sync_client.is_closed:
            self._sync_client.close()
            self._sync_client = None

    async def close_async(self) -> None:
        """Close the asynchronous HTTP client."""
        if self._async_client and not self._async_client.is_closed:
            await self._async_client.aclose()
            self._async_client = None

    def close(self) -> None:
        """Close all HTTP clients."""
        self.close_sync()

    async def aclose(self) -> None:
        """Close all async HTTP clients."""
        await self.close_async()

    def __enter__(self) -> HTTPClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    async def __aenter__(self) -> HTTPClient:
        return self

    async def __aexit__(self, *args) -> None:
        await self.aclose()
