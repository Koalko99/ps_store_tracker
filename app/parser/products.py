from __future__ import annotations

from json import JSONDecodeError, dumps, loads
from re import findall
from typing import Any

from bs4 import BeautifulSoup

from app.core.errors import ParserError
from app.parser.models.product import Product, ProductPageDetails, ProductPrice, Localization

BASE_CTA_TYPES = {"ADD_TO_CART", "PREORDER", "BUY_NOW"}
INCLUDED_LABELS = {"Входит в подписку", "Included"}
DEMO_NAMES = {
    "демоверсия",
    "полная ознакомительная версия игры",
    "demo"
}
TAG_REPLACEMENTS = {
    "™": "",
    "®": "",
    "©": "",
    "℗": "",
    "℠": ""
}


def parse_region(url: str) -> str:
    try:
        return url.split("/")[3]
    except IndexError as exc:
        msg = f"Cannot parse region from URL: {url}"
        raise ParserError(msg) from exc


def parse_product_page(product_id: str, html: str) -> ProductPageDetails:
    soup = BeautifulSoup(html, "html.parser")
    next_data = _extract_next_data(soup)
    game_info = _extract_game_info(soup)

    return ProductPageDetails(
        product_id=product_id,
        platforms=_split_csv(_read_dd(game_info, "gameInfo#releaseInformation#platform-value")),
        publisher=_read_dd(game_info, "gameInfo#releaseInformation#publisher-value"),
        voice_languages=_read_languages(
            game_info,
            [
                "gameInfo#releaseInformation#voice-value",
                "gameInfo#releaseInformation#ps5Voice-value",
                "gameInfo#releaseInformation#ps4Voice-value",
            ],
        ),
        subtitles=_read_languages(
            game_info,
            [
                "gameInfo#releaseInformation#subtitles-value",
                "gameInfo#releaseInformation#ps5Subtitles-value",
                "gameInfo#releaseInformation#ps4Subtitles-value",
            ],
        ),
        description=_extract_batarang_text(next_data, "overview"),
        ext_info=_extract_compatibility_notice(next_data),
        rating=_extract_rating(product_id, next_data),
        master_image=_extract_background_master_image(product_id, next_data),
    )


def parse_products(
    url: str,
    product_payload: dict[str, Any],
    price_payload: dict[str, Any],
    details_by_id: dict[str, ProductPageDetails],
) -> list[Product]:
    region = parse_region(url)
    product_retrieve = _read_product_retrieve(product_payload)
    price_retrieve = _read_product_retrieve(price_payload)

    concept = product_retrieve.get("concept") or {}
    main_name = concept.get("name") or product_retrieve.get("name") or ""
    products = concept.get("products") or []

    if products and product_retrieve.get("topCategory") != "ADD_ON":
        return [
            product
            for product in (
                _build_game_product(region, main_name, raw_product, details_by_id)
                for raw_product in products
            )
            if product is not None
        ]

    addon = _build_addon_product(region, main_name, price_retrieve, details_by_id)
    return [addon] if addon else []


def product_ids_to_load(
    product_payload: dict[str, Any],
    price_payload: dict[str, Any],
) -> list[str]:
    product_retrieve = _read_product_retrieve(product_payload)
    price_retrieve = _read_product_retrieve(price_payload)
    concept = product_retrieve.get("concept") or {}
    products = concept.get("products") or []

    if products and product_retrieve.get("topCategory") != "ADD_ON":
        return [product["id"] for product in products if product.get("id")]

    product_id = price_retrieve.get("id")
    return [product_id] if product_id else []


def _build_game_product(
    region: str,
    main_name: str,
    raw_product: dict[str, Any],
    details_by_id: dict[str, ProductPageDetails],
) -> Product | None:
    product_id = raw_product["id"]
    details = details_by_id.get(product_id)
    if details is None or not details.publisher:
        return None

    price = extract_price(raw_product.get("webctas") or [])
    product_type = price.product_type_override or infer_product_type(raw_product)
    if not product_type:
        return None

    if not price.price:
        price.price = price.old_price
    if region == "en-in":
        price = multiply_price(price, 100)

    if not price.price:
        return None

    name = raw_product.get("name") or ""
    edition, compound = extract_edition(raw_product, name)
    tags = normalize_tags(
        {
            main_name,
            name,
            raw_product.get("invariantName") or "",
        },
    )

    return Product(
        id=product_id,
        category=extract_categories(raw_product),
        region=region,
        type=product_type,
        name=name,
        main_name=main_name,
        edition=edition,
        description=details.description,
        image=extract_master_image(raw_product) or details.master_image,
        compound=compound,
        platforms=details.platforms,
        publisher=details.publisher,
        localization=Localization(
            voice_languages={
                data_type: (value.split(', ') if value else [])
                for data_type, value
                in details.voice_languages.items()
                },
            subtitles={
                data_type: (value.split(', ') if value else [])
                for data_type, value
                in details.subtitles.items()
                }
        ),
        rating=details.rating,
        info=loads(details.ext_info),
        tags=tags,
        **price.model_dump(),
    )


def _build_addon_product(
    region: str,
    main_name: str,
    raw_product: dict[str, Any],
    details_by_id: dict[str, ProductPageDetails],
) -> Product | None:
    product_id = raw_product.get("id")
    if not product_id:
        return None

    details = details_by_id.get(product_id)
    if details is None or not details.publisher:
        return None

    price = extract_price(raw_product.get("webctas") or [])
    if not price.price:
        price.price = price.old_price
    if region == "en-in":
        price = multiply_price(price, 100)
    if not price.price:
        return None

    name = raw_product.get("name") or ""
    sku_name = _first_sku_name(raw_product)

    return Product(
        id=product_id,
        category=[sku_name] if sku_name else [],
        region=region,
        type=price.product_type_override or "Addon",
        name=name,
        main_name=main_name,
        edition=sku_name,
        description=details.description,
        image=details.master_image,
        compound="",
        platforms=details.platforms,
        publisher=details.publisher,
        localization=Localization(
            voice_languages=details.voice_languages.split(", ") if details.voice_languages else [],
            subtitles=details.subtitles.split(", ") if details.subtitles else []
        ),
        rating=details.rating,
        info=details.ext_info,
        tags=normalize_tags({main_name, name, raw_product.get("invariantName") or ""}),
        **price.model_dump(),
    )


def extract_price(webctas: list[dict[str, Any]]) -> ProductPrice:
    result = ProductPrice()

    for cta in webctas:
        cta_type = cta.get("type") or ""
        price = _normalize_price_node(cta.get("price") or {})

        if cta_type == "PREORDER":
            result.product_type_override = "Preorder"

        if _is_base_price_cta(cta_type):
            if price.get("discountedPrice") and not result.price:
                result.price = _money(price.get("discountedValue"))
            if price.get("basePrice") and not result.old_price:
                result.old_price = _money(price.get("basePriceValue"))
            if price.get("discountText"):
                result.discount = price["discountText"]
            if price.get("endTime"):
                result.discount_end = _timestamp_to_datetime(price["endTime"])

        if "PS_PLUS" in cta_type and price.get("discountedPrice") in INCLUDED_LABELS:
            result.ps_plus = True
        if "EA_ACCESS" in cta_type and price.get("discountedPrice") in INCLUDED_LABELS:
            result.ea_access = True
        if cta_type == "UPSELL_PS_PLUS_DISCOUNT":
            result.ps_price = _money(price.get("discountedValue"))
        if cta_type == "UPSELL_EA_ACCESS_DISCOUNT":
            result.ea_price = _money(price.get("discountedValue"))

    return result


def infer_product_type(product: dict[str, Any]) -> str:
    name = product.get("name") or ""
    if "подписка" in name.lower() or "subscription" in name.lower():
        return "Подписка"
    if product.get("topCategory") == "GAME":
        return "Game"

    sku_name = _first_sku_name(product)
    if not sku_name:
        return "Game"

    lowered = sku_name.lower()
    if lowered in DEMO_NAMES or "full game trial" in lowered:
        return "Game"
    return sku_name


def extract_categories(product: dict[str, Any]) -> list[str]:
    genres = product.get("localizedGenres") or []
    return sorted({genre["value"] for genre in genres if genre.get("value")})


def extract_edition(product: dict[str, Any], fallback_name: str) -> tuple[str, str]:
    edition = product.get("edition") or {}
    features = edition.get("features") or []
    edition_name = edition.get("name") or fallback_name
    compound = dumps(features, ensure_ascii=False) if features else ""
    return edition_name, compound


def extract_master_image(product: dict[str, Any]) -> str:
    for image in product.get("media") or []:
        if image.get("role") == "MASTER" and image.get("url"):
            return image["url"]
    return ""

def normalize_tags(tags: set[str]) -> set[str]:
    normalized: set[str] = set()
    for tag in tags:
        value = tag.strip()
        for old, new in TAG_REPLACEMENTS.items():
            value = value.replace(old, new)
        if value:
            normalized.add(value)
    return normalized


def multiply_price(price: ProductPrice, factor: float) -> ProductPrice:
    data = price.model_dump()
    for key in ("price", "old_price", "ps_price", "ea_price"):
        if data[key] is not None:
            data[key] *= factor
    return ProductPrice.model_validate(data)


def _extract_game_info(soup: BeautifulSoup):
    game_info = soup.select_one("main .pdp-main.psw-dark-theme [data-qa='gameInfo'] dl")
    if game_info is None:
        raise ParserError("Product page game info block was not found")
    return game_info


def _extract_next_data(soup: BeautifulSoup) -> dict[str, Any]:
    script = soup.find("script", {"id": "__NEXT_DATA__", "type": "application/json"})
    if script is None or not script.text:
        raise ParserError("Product page __NEXT_DATA__ script was not found")
    try:
        return loads(script.text)
    except JSONDecodeError as exc:
        raise ParserError("Product page __NEXT_DATA__ contains invalid JSON") from exc


def _read_dd(game_info: Any, data_qa: str) -> str:
    node = game_info.find("dd", {"data-qa": data_qa})
    return node.get_text(strip=True) if node else ""


def _read_languages(game_info: Any, data_qas: list[str]) -> dict:
    result = {
        "main": "",
        "ps4": "",
        "ps5": ""
    }
    for data_qa in data_qas:
        data_type = "main"
        if "ps4" in data_qa:
            data_type = "ps4"
        elif "ps5" in data_qa:
            data_type = "ps5"
        result.update({data_type: _read_dd(game_info, data_qa)})

    return result


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _extract_batarang_text(next_data: dict[str, Any], key: str) -> str:
    raw_html = _read_batarang(next_data, key)
    return BeautifulSoup(raw_html, "html.parser").get_text("\n\n", strip=True) if raw_html else ""


def _extract_compatibility_notice(next_data: dict[str, Any]) -> str:
    raw_html = _read_batarang(next_data, "compatibility-notices")
    values = findall(r">([^<]+)</", raw_html)
    return dumps(values[1:], ensure_ascii=False) if len(values) > 1 else raw_html


def _extract_rating(product_id: str, next_data: dict[str, Any]) -> float:
    raw_html = _read_batarang(next_data, "star-rating")
    values = findall(r">(.+)</script", raw_html)
    if not values:
        return 0
    try:
        rating_payload = loads(values[0])
        product_rating = rating_payload["cache"][f"Product:{product_id}"]["starRating"]
        return float(product_rating["averageRating"])
    except (JSONDecodeError, KeyError, TypeError, ValueError):
        return 0


def _extract_background_master_image(product_id: str, next_data: dict[str, Any]) -> str:
    raw_html = _read_batarang(next_data, "background-image")
    values = findall(r">([^<]+)</", raw_html)
    if not values:
        return ""
    try:
        payload = loads(values[0])
        media = payload["cache"][f"Product:{product_id}"]["media"]
    except (JSONDecodeError, KeyError, TypeError):
        return ""

    for image in media:
        if image.get("role") == "MASTER" and image.get("url"):
            return image["url"]
    return ""


def _read_batarang(next_data: dict[str, Any], key: str) -> str:
    try:
        value = next_data["props"]["pageProps"]["batarangs"][key]["text"]
        return value if isinstance(value, str) else ""
    except KeyError:
        return ""


def _read_product_retrieve(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        product = payload["data"]["productRetrieve"]
    except (KeyError, TypeError) as exc:
        raise ParserError("Product GraphQL response has unexpected structure") from exc
    return product or {}


def _is_base_price_cta(cta_type: str) -> bool:
    return cta_type in BASE_CTA_TYPES


def _normalize_price_node(price: dict[str, Any]) -> dict[str, Any]:
    nested_price = price.get("price")
    return nested_price if isinstance(nested_price, dict) else price


def _money(value: Any) -> float:
    return float(value or 0) / 100


def _timestamp_to_datetime(value: Any):
    try:
        from datetime import datetime

        return datetime.fromtimestamp(int(value) // 1000)
    except (TypeError, ValueError, OSError):
        return None


def _first_sku_name(product: dict[str, Any]) -> str:
    skus = product.get("skus") or []
    if not skus:
        return ""
    return skus[0].get("name") or ""
