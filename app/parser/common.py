from __future__ import annotations

from json import dumps
from random import choice
from typing import Any

API_URL = "https://web.np.playstation.com/api/graphql/v1/op"

USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) "
    "Gecko/20100101 Firefox/122.0",
)


def random_user_agent() -> str:
    return choice(USER_AGENTS)


def page_headers() -> dict[str, str]:
    return {
        "accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
            "image/webp,image/apng,*/*;q=0.8"
        ),
        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "upgrade-insecure-requests": "1",
        "user-agent": random_user_agent(),
    }


def json_headers(store_url: str) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Accept-Language": "en-US",
        "apollographql-client-name": "@sie-private/web-commerce-anywhere",
        "apollographql-client-version": "3.23.0",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "Origin": "https://store.playstation.com",
        "Pragma": "no-cache",
        "Referer": "https://store.playstation.com/",
        "User-Agent": random_user_agent(),
        "x-psn-store-locale-override": store_url.split("/")[-3],
    }


def graphql_params(store_url: str) -> dict[str, Any] | list[dict[str, Any]]:
    product_type, sku = store_url.rstrip("/").split("/")[-2:]
    queries: dict[str, dict[str, Any] | list[dict[str, Any]]] = {
        "concept": {
            "operationName": "conceptRetrieveForCtasWithPrice",
            "variables": dumps({"conceptId": sku}),
            "extensions": dumps(
                {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": (
                            "eab9d873f90d4ad98fd55f07b6a0a606e6b3925f2d03b70477234b79c1df30b5"
                        ),
                    },
                },
            ),
        },
        "product": [
            {
                "operationName": "productRetrieveForCtasWithPrice",
                "variables": dumps({"productId": sku}),
                "extensions": dumps(
                    {
                        "persistedQuery": {
                            "version": 1,
                            "sha256Hash": (
                                "8872b0419dcab2fea5916ef698544c237b1096f9e76acc6aacf629551adee8cd"
                            ),
                        },
                    },
                ),
            },
            {
                "operationName": "productRetrieveForUpsellWithCtas",
                "variables": dumps({"productId": sku}),
                "extensions": dumps(
                    {
                        "persistedQuery": {
                            "version": 1,
                            "sha256Hash": (
                                "fb0bfa0af4d8dc42b28fa5c077ed715543e7fb8a3deff8117a50b99864d246f1"
                            ),
                        },
                    },
                ),
            },
        ],
    }

    return queries[product_type]


def product_graphql_params(store_url: str) -> tuple[dict[str, Any], dict[str, Any]]:
    params = graphql_params(store_url)
    if not isinstance(params, list) or len(params) != 2:
        msg = f"Expected product URL, got: {store_url}"
        raise ValueError(msg)

    price_params, upsell_params = params
    return price_params, upsell_params


def client_kwargs(url: str, request_type: str) -> dict[str, Any]:
    if request_type == "page":
        return {"url": url, "headers": page_headers()}
    if request_type == "json":
        return {"url": API_URL, "headers": json_headers(url), "params": graphql_params(url)}

    msg = f"Unsupported request type: {request_type}"
    raise ValueError(msg)
