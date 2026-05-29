from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable

from app.core.config import AppSettings, load_settings
from app.core.logging import get_logger
from app.parser.client import HttpClient
from app.parser.common import API_URL, json_headers, page_headers, product_graphql_params
from app.parser.models.product import Product
from app.parser.parser import (
    concept_to_product,
    extract_concepts,
    get_pages,
    ps_plus_combine,
    ps_plus_extract,
)
from app.parser.products import parse_product_page, parse_products, product_ids_to_load

PS_PLUS_CATEGORIES = (
    "plus-games-list",
    "ubisoft-classics-list",
    "plus-classics-list",
    "plus-monthly-games-list",
)


class PlaystationStoreService:
    def __init__(
        self,
        settings: AppSettings | None = None,
        config_path: str = "config.json",
        client: HttpClient | None = None,
    ) -> None:
        self.logger = get_logger(__name__)
        self.settings = settings or load_settings(config_path)
        self.client = client or HttpClient(
            request_timeout=self.settings.request_timeout,
            connections_limit=self.settings.connections_limit,
            max_retries=self.settings.max_retries,
            sleep_on_exc=self.settings.sleep_on_exception,
            sleep_on_blocking=self.settings.access_denied_check_interval,
            proxies=self.settings.proxies,
        )

    async def fetch_ps_plus(self, region: str):
        url = "https://www.playstation.com/bin/imagic/gameslist"
        self.logger.info("Extracting PlayStation Plus data: region=%s", region)

        async with self.client as session:
            responses = await asyncio.gather(
                *[
                    session.raw_with_flag(
                        flag=category,
                        url=url,
                        params={"locale": region, "categoryList": category},
                        batch_size=self.settings.inf_batch,
                    )
                    for category in PS_PLUS_CATEGORIES
                ],
            )

        extracted = [ps_plus_extract(flag, text) for flag, text in responses]
        return ps_plus_combine(region=region, json=extracted)

    async def fetch_page_urls(self, region: str) -> list[str]:
        url = f"https://store.playstation.com/{region}/pages/browse"
        self.logger.info("Extracting browse pages: region=%s", region)

        async with self.client as session:
            response = await session.fetch_page(url=url, batch_size=self.settings.inf_batch)

        return get_pages(response)

    async def fetch_concept_urls(self, urls: Iterable[str]) -> list[str]:
        url_list = list(urls)
        result: list[str] = []
        batch_size = self.settings.batch_size_pages

        self.logger.info("Extracting concept URLs: pages=%s", len(url_list))

        async with self.client as session:
            for offset in range(0, len(url_list), batch_size):
                if offset > 0:
                    await asyncio.sleep(self.settings.sleep_between_batches)

                batch = url_list[offset : offset + batch_size]
                responses = await asyncio.gather(
                    *[session.fetch_page(url=url, batch_size=batch_size) for url in batch],
                )

                for response in responses:
                    result.extend(extract_concepts(response))

                self._log_progress("Concept extraction", offset, batch_size, len(url_list))

        return result

    async def resolve_product_urls(self, urls: Iterable[str]) -> list[str]:
        url_list = list(dict.fromkeys(urls))
        result = [url for url in url_list if "/product/" in url]
        concept_urls = [url for url in url_list if "/product/" not in url]
        batch_size = self.settings.batch_size_unquote

        self.logger.info("Resolving concept URLs to product URLs: concepts=%s", len(concept_urls))

        async with self.client as session:
            for offset in range(0, len(concept_urls), batch_size):
                if offset > 0:
                    await asyncio.sleep(self.settings.sleep_between_batches)

                batch = concept_urls[offset : offset + batch_size]
                responses = await asyncio.gather(
                    *[
                        session.get_with_flag(
                            flag=url.split("/")[3],
                            url=url,
                            batch_size=batch_size,
                        )
                        for url in batch
                    ],
                )

                for region, response in responses:
                    result.extend(concept_to_product(region, response))

                self._log_progress("Product URL resolution", offset, batch_size, len(concept_urls))

        return list(dict.fromkeys(result))

    async def collect_product_urls(self, region: str) -> list[str]:
        pages = await self.fetch_page_urls(region)
        concepts = await self.fetch_concept_urls(pages)
        return await self.resolve_product_urls(concepts)

    async def fetch_products(self, url: str) -> list[Product]:
        region = url.split("/")[3]
        price_params, product_params = product_graphql_params(url)

        async with self.client as session:
            product_payload, price_payload = await asyncio.gather(
                session.request_text(
                    url=API_URL,
                    params=product_params,
                    headers=json_headers(url),
                    batch_size=self.settings.inf_batch,
                ),
                session.request_text(
                    url=API_URL,
                    params=price_params,
                    headers=json_headers(url),
                    batch_size=self.settings.inf_batch,
                ),
            )

            product_payload_json = json.loads(product_payload)
            price_payload_json = json.loads(price_payload)
            product_ids = product_ids_to_load(product_payload_json, price_payload_json)

            detail_pages = await asyncio.gather(
                *[
                    session.request_text(
                        url=f"https://store.playstation.com/{region}/product/{product_id}",
                        headers=page_headers(),
                        batch_size=self.settings.inf_batch,
                    )
                    for product_id in product_ids
                ],
            )

        details = {
            product_id: parse_product_page(product_id, html)
            for product_id, html in zip(product_ids, detail_pages, strict=False)
        }
        return parse_products(url, product_payload_json, price_payload_json, details)

    async def ps_plus(self, region: str):
        return await self.fetch_ps_plus(region)

    async def pages(self, region: str) -> list[str]:
        return await self.fetch_page_urls(region)

    async def concepts(self, urls: Iterable[str]) -> list[str]:
        return await self.fetch_concept_urls(urls)

    async def unquote(self, urls: Iterable[str]) -> list[str]:
        return await self.resolve_product_urls(urls)

    async def parse(self, url: str) -> list[Product]:
        return await self.fetch_products(url)

    def _log_progress(self, label: str, offset: int, batch_size: int, total: int) -> None:
        if total == 0:
            return

        progress = round(min((offset + batch_size) * 100 / total, 100), 2)
        self.logger.info("%s progress: %s%%", label, progress)


Service = PlaystationStoreService
