from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.logging import get_logger


class RegionSettings(BaseModel):
    code: str = Field(pattern=r"^[a-z]{2}-[a-z]{2}$")
    divide_price_by_100: bool = False


class AppSettings(BaseModel):
    max_retries: int = Field(default=3, ge=1)
    request_timeout: float = Field(default=120, gt=0)
    batch_size_pages: int = Field(default=30, ge=1)
    batch_size_products: int = Field(default=70, ge=1)
    batch_size_unquote: int = Field(default=250, ge=1)
    sleep_between_batches: float = Field(default=3, ge=0)
    connections_limit: int = Field(default=300, ge=1)
    sleep_on_exception: float = Field(default=5, ge=0)
    access_denied_check_interval: float = Field(default=60, ge=0)
    inf_batch: int = Field(default=10**18, ge=1)
    regions: list[RegionSettings] = Field(
        default_factory=lambda: [
            RegionSettings(code="ru-ua", divide_price_by_100=False),
        ],
    )
    proxies: list[str] = Field(default_factory=list)

    @field_validator("proxies")
    @classmethod
    def validate_proxies(cls, value: list[str]) -> list[str]:
        return [proxy for proxy in value if proxy.startswith(("http://", "https://"))]

    @property
    def region_codes(self) -> list[str]:
        return [region.code for region in self.regions]



def load_settings(config_path: str | Path = "config.json") -> AppSettings:
    logger = get_logger(__name__)

    data: dict[str, Any] = {}
    path = Path(config_path)

    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            msg = f"Invalid JSON config file: {path}"
            raise RuntimeError(msg) from exc
    else:
        logger.warning("Config file does not exist, using defaults: %s", path)

    if "PROXIES" in data and "proxies" not in data:
        data["proxies"] = data.pop("PROXIES")

    try:
        return AppSettings.model_validate(data)
    except ValidationError as exc:
        msg = f"Invalid application settings in {path}"
        raise RuntimeError(msg) from exc


Config = AppSettings
