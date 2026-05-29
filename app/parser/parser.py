from __future__ import annotations

from json import JSONDecodeError, loads
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.core.errors import ParserError
from app.parser.models.ps_plus import PlaystationPlus, PsPlusGame


def _require_tag(node: Tag | BeautifulSoup | None, selector: str) -> Tag:
    if node is None:
        msg = f"Cannot search for selector on empty node: {selector}"
        raise ParserError(msg)

    found = node.select_one(selector)
    if not isinstance(found, Tag):
        msg = f"Required selector was not found: {selector}"
        raise ParserError(msg)
    return found


def get_pages(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    html_tag = _require_tag(soup, "html")
    region = html_tag.get("lang")

    if not isinstance(region, str) or not region:
        raise ParserError("HTML document does not contain a region in html[lang]")

    pagination_items = soup.select("#__next main section.ems-sdk-grid nav ol li span")
    if not pagination_items:
        raise ParserError("Browse page pagination was not found")

    try:
        count = int(pagination_items[-1].get_text(strip=True))
    except ValueError as exc:
        msg = "Browse page pagination count is not an integer"
        raise ParserError(msg) from exc

    return [
        f"https://store.playstation.com/{region}/pages/browse/{page}"
        for page in range(1, count + 1)
    ]


def get_names(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    products = soup.select("#__next main section.ems-sdk-grid ul.psw-grid-list li")

    names: list[str] = []
    for product in products:
        link = product.find("a")
        if not isinstance(link, Tag):
            continue

        raw_meta = link.get("data-telemetry-meta")
        if not isinstance(raw_meta, str):
            continue

        try:
            names.append(loads(raw_meta)["name"])
        except (JSONDecodeError, KeyError, TypeError) as exc:
            raise ParserError("Product telemetry metadata has unexpected structure") from exc

    return names


def ps_plus_extract(flag: str, text: str) -> tuple[str, list[dict[str, Any]]]:
    try:
        payload = loads(text)
        games = [game for section in payload for game in section["games"]]
    except (JSONDecodeError, KeyError, TypeError) as exc:
        msg = f"PS Plus response has unexpected structure: {flag}"
        raise ParserError(msg) from exc

    return flag, games


def ps_plus_combine(region: str, json: list[tuple[str, list[dict[str, Any]]]]) -> PlaystationPlus:
    essential: list[PsPlusGame] = []
    extra: list[PsPlusGame] = []
    premium: list[PsPlusGame] = []

    for flag, payload in json:
        games = [
            PsPlusGame(name=item["name"], product_id=item["productId"])
            for item in payload
            if item.get("name") and item.get("productId")
        ]

        if flag == "plus-monthly-games-list":
            essential.extend(games)
            extra.extend(games)
            premium.extend(games)
        elif flag in {"plus-games-list", "ubisoft-classics-list"}:
            extra.extend(games)
            premium.extend(games)
        elif flag == "plus-classics-list":
            premium.extend(games)

    return PlaystationPlus(region=region, essential=essential, extra=extra, premium=premium)


def extract_concepts(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    products = soup.select("#__next main section.ems-sdk-grid ul.psw-grid-list li a[href]")

    if not products:
        raise ParserError("No product links were found on browse page")

    urls: list[str] = []
    for product in products:
        href = product.get("href")
        if isinstance(href, str):
            urls.append(f"https://store.playstation.com{href}")

    return urls


def concept_to_product(region: str, json: dict[str, Any]) -> list[str]:
    try:
        products = json["data"]["conceptRetrieve"]["products"]
    except (KeyError, TypeError) as exc:
        msg = "Concept GraphQL response has unexpected structure"
        raise ParserError(msg) from exc

    result: list[str] = []
    for product in products:
        product_id = product.get("id")
        if isinstance(product_id, str) and product_id:
            result.append(f"https://store.playstation.com/{region}/product/{product_id}")

    return result
