import asyncio
from json import loads
from typing import List, Dict, Set, Any
import app.core.logging as logging
from aiohttp import ClientTimeout, ClientSession, TCPConnector
from app.parser.common import client_kwargs

class Client:

    def __init__(self,
                 batch_size: int,
                 request_timeout: float = 10,
                 connections_limit: int = 200,
                 max_retries: int = 3,
                 sleep_on_exc: int = 5,
                 sleep_on_blocking: int = 60,
                 proxies: List[str] = None):
    
        self.session: ClientSession = None

        self.__proxy__ = ""
        self.__requests_count__ = 0
        self.sleep_on_exc = sleep_on_exc
        self.max_retries = max_retries
        self.sleep_on_blocking = sleep_on_blocking
        self._proxy_lock = asyncio.Lock()
        self.proxies = proxies or []
        
        self.batch_size = batch_size
        self.connections_limit = connections_limit
        self.logger = logging.get_logger(__name__)
        self.timeout = ClientTimeout(total=request_timeout)


    async def __aenter__(self):
        self.session = ClientSession(
            timeout=self.timeout,
            connector=TCPConnector(limit=self.connections_limit),
        )

        return self


    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()


    async def get(self, url: str, json: bool = False) -> str | List[Any] | Dict[Any]:

        if self.__requests_count__ % self.batch_size == 0:
            self.__proxy__ = await self._get_proxy()

        counter = 0
        
        request_type = "page" if json == False else "json"

        request_kwargs = client_kwargs(url, request_type)

        while counter < self.max_retries:
            try:
                async with self.session.get(proxy=self.__proxy__, **request_kwargs) as resp:
                    text = await resp.text()
                    
                    if "You don't have permission to access" in text:
                        counter = 0
                        self.__proxy__ = await self._get_proxy()

                        await asyncio.sleep(self.sleep_on_blocking)
                        continue

                    if request_type == "json":
                        text = loads(text)

                    return text

            except (asyncio.CancelledError, KeyboardInterrupt):
                return ""
            except:
                counter += 1
                await asyncio.sleep(self.sleep_on_exc)
        else:
            return ""


    async def get_with_flag(self, flag: str, **kwargs) -> Set[str, Any]:
        data = await self.get(**kwargs)
        return flag, data

    async def _get_proxy(self) -> str | None:
        if not self.proxies:
            return None

        self.logger.warning("Setting new proxy")

        async with self._proxy_lock:
            proxy = self.proxies[self.proxy_index]

            self.proxy_index += 1

            if self.proxy_index >= len(self.proxies):
                self.proxy_index = 0

            return proxy

    async def _refresh_session(self) -> None:
        if self.session:
            await self.session.close()

        self.logger.warning("Refreshing the session")

        self.session = self.session = ClientSession(
            timeout=self.timeout,
            connector=TCPConnector(limit=self.connections_limit)
        )
