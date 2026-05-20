import asyncio
from json import loads
from typing import List
import app.core.logging as logging
from aiohttp import ClientTimeout, ClientSession, TCPConnector
from app.parser.common import header, page_headers, json_headers, get_params

class Client:

    def __init__(self,
                 batch_size: int,
                 request_timeout: float = 10,
                 connections_limit: int = 200,
                 max_retries: int = 3,
                 sleep_on: int = 5,
                 proxies: List[str] = None):
    
        self.session: ClientSession = None

        self.API_URL = "https://web.np.playstation.com/api/graphql/v1/op"

        self.__proxy__ = ""
        self.__requests_count__ = 0
        self.sleep_on = sleep_on
        self.max_retries = max_retries
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


    async def get_page(self, url: str):

        if self.__requests_count__ % self.batch_size == 0:
            self.__proxy__ = await self._get_proxy()

        counter = 0
        
        while counter < self.max_retries:
            try:
                async with self.session.get(url, headers=page_headers(), proxy=self.__proxy__) as resp:
                    return await resp.text()
            except (asyncio.CancelledError, KeyboardInterrupt):
                return []
            except:
                counter += 1
                await asyncio.sleep(self.sleep_on)
        else:
            return []


    async def get_json(self, url: str):

        if self.__requests_count__ % self.batch_size == 0:
            self.__proxy__ = await self._get_proxy()

        counter = 0
        
        while counter < self.max_retries:
            try:
                async with self.session.get(self.API_URL, headers=json_headers(url), params=get_params(url), proxy=self.__proxy__) as resp:
                    text = await resp.text()
                
                return loads(text)

            except (asyncio.CancelledError, KeyboardInterrupt):
                return []
            except:
                counter += 1
                await asyncio.sleep(self.sleep_on)
        else:
            return []

    async def _get_proxy(self) -> str | None:
        if not self.proxies:
            return None

        async with self._proxy_lock:
            proxy = self.proxies[self.proxy_index]

            self.proxy_index += 1

            if self.proxy_index >= len(self.proxies):
                self.proxy_index = 0

            return proxy
