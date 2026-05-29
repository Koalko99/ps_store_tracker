from __future__ import annotations

import asyncio
from json import JSONDecodeError, loads
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout, TCPConnector

from app.core.errors import AccessDeniedError, HttpClientError
from app.core.logging import get_logger
from app.parser.common import client_kwargs

ACCESS_DENIED_MARKER = "You don't have permission to access"


class HttpClient:
    def __init__(
        self,
        request_timeout: float = 10,
        connections_limit: int = 300,
        max_retries: int = 3,
        sleep_on_exc: float = 5,
        sleep_on_blocking: float = 60,
        proxies: list[str] | None = None,
    ) -> None:
        self.session: ClientSession | None = None
        self.active_proxy: str | None = None
        self.requests_count = 0
        self.proxy_index = 0
        self.sleep_on_exc = sleep_on_exc
        self.max_retries = max_retries
        self.sleep_on_blocking = sleep_on_blocking
        self.proxy_lock = asyncio.Lock()
        self.proxies = proxies or []
        self.connections_limit = connections_limit
        self.logger = get_logger(__name__)
        self.timeout = ClientTimeout(total=request_timeout)

    async def __aenter__(self) -> HttpClient:
        self.logger.info("Creating HTTP session")
        self.session = ClientSession(
            timeout=self.timeout,
            connector=TCPConnector(limit=self.connections_limit),
        )
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self.session and not self.session.closed:
            self.logger.info("Closing HTTP session")
            await self.session.close()

    async def fetch_page(self, url: str, batch_size: int) -> str:
        return await self.request_text(batch_size=batch_size, **client_kwargs(url, "page"))

    async def fetch_json(self, url: str, batch_size: int) -> Any:
        text = await self.request_text(batch_size=batch_size, **client_kwargs(url, "json"))
        try:
            return loads(text)
        except JSONDecodeError as exc:
            msg = f"Invalid JSON response for {url}"
            raise HttpClientError(msg) from exc

    async def request_text(self, batch_size: int, **kwargs: Any) -> str:
        if self.session is None:
            msg = "HTTP client must be used as an async context manager"
            raise RuntimeError(msg)

        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            await self._rotate_proxy_if_needed(batch_size)
            self.requests_count += 1

            try:
                async with self.session.get(proxy=self.active_proxy, **kwargs) as response:
                    text = await response.text()

                    if ACCESS_DENIED_MARKER in text:
                        await self._handle_access_denied(kwargs.get("url", "unknown"))
                        continue

                    if response.status >= 400:
                        msg = f"HTTP {response.status} for {kwargs.get('url', 'unknown')}"
                        raise HttpClientError(msg)

                    return text
            except asyncio.CancelledError:
                raise
            except (ClientError, TimeoutError, HttpClientError, AccessDeniedError) as exc:
                last_error = exc
                self.logger.warning(
                    "HTTP request failed: url=%s attempt=%s/%s error=%s",
                    kwargs.get("url", "unknown"),
                    attempt,
                    self.max_retries,
                    exc,
                )

                if attempt < self.max_retries:
                    await asyncio.sleep(self._retry_delay(attempt))

        msg = (
            f"HTTP request failed after {self.max_retries} attempts: "
            f"{kwargs.get('url', 'unknown')}"
        )
        raise HttpClientError(msg) from last_error

    async def get_with_flag(self, flag: str, **kwargs: Any) -> tuple[str, Any]:
        data = await self.fetch_json(**kwargs)
        return flag, data

    async def page_with_flag(self, flag: str, **kwargs: Any) -> tuple[str, str]:
        data = await self.fetch_page(**kwargs)
        return flag, data

    async def raw_with_flag(self, flag: str, **kwargs: Any) -> tuple[str, str]:
        data = await self.request_text(**kwargs)
        return flag, data

    async def _rotate_proxy_if_needed(self, batch_size: int) -> None:
        if batch_size <= 0:
            return
        if self.requests_count % batch_size == 0:
            self.active_proxy = await self._next_proxy()

    async def _next_proxy(self) -> str | None:
        if not self.proxies:
            return None

        async with self.proxy_lock:
            proxy = self.proxies[self.proxy_index]
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
            self.logger.info("Using proxy: %s", proxy)
            return proxy

    async def _handle_access_denied(self, url: str) -> None:
        self.active_proxy = await self._next_proxy()
        self.logger.warning("Access denied detected for %s", url)
        await asyncio.sleep(self.sleep_on_blocking)
        raise AccessDeniedError(f"Access denied for {url}")

    def _retry_delay(self, attempt: int) -> float:
        return self.sleep_on_exc * attempt


Client = HttpClient
