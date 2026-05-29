from __future__ import annotations

import argparse
import asyncio
from json import dumps

from app.core.config import load_settings
from app.core.logging import setup_logging
from app.parser.service import PlaystationStoreService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ps-store-tracker")
    parser.add_argument("--config", default="config.json", help="Path to JSON config file")
    parser.add_argument("--log-level", default="INFO", help="Python logging level")

    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="Collect product URLs for a region")
    collect.add_argument(
        "--region",
        required=True,
        help="PlayStation Store locale, for example ru-ua",
    )

    ps_plus = subparsers.add_parser("ps-plus", help="Collect PlayStation Plus catalog data")
    ps_plus.add_argument(
        "--region",
        required=True,
        help="PlayStation Store locale",
    )

    product = subparsers.add_parser("product", help="Parse one PlayStation Store product URL")
    product.add_argument("--url", "-u", required=True, help="PlayStation Store product URL")

    return parser


async def run(args: argparse.Namespace) -> None:
    settings = load_settings(args.config)
    service = PlaystationStoreService(settings=settings)

    if args.command == "collect":
        products = await service.collect_product_urls(args.region)
        print(len(products))
        return

    if args.command == "ps-plus":
        catalog = await service.fetch_ps_plus(args.region)
        print(catalog.model_dump_json())
        return

    if args.command == "product":
        products = await service.fetch_products(args.url)
        for product in products:
            print(dumps(product.model_dump(by_alias=True, mode="json")))
        return

    msg = f"Unsupported command: {args.command}"
    raise ValueError(msg)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(level=args.log_level)
    asyncio.run(run(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
