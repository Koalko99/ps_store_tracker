from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductPageDetails(BaseModel):
    product_id: str
    platforms: list[str] = Field(default_factory=list)
    publisher: str = ""
    voice_languages: dict = Field(default_factory=dict)
    subtitles: dict = Field(default_factory=dict)
    description: str = ""
    ext_info: str = ""
    rating: float = 0
    master_image: str = ""

class Localization(BaseModel):
    voice_languages: dict = Field(default_factory=dict)
    subtitles: dict = Field(default_factory=dict)

class ProductPrice(BaseModel):
    price: float = 0
    old_price: float = 0
    ps_price: float | None = None
    ea_price: float | None = None
    ps_plus: bool = False
    ea_access: bool = False
    discount: str = ""
    discount_end: datetime | None = None
    product_type_override: str | None = None


class Product(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    category: list[str] = Field(default_factory=list)
    region: str
    product_type: str = Field(alias="type")
    name: str
    main_name: str
    edition: str = ""
    description: str = ""
    image: str = ""
    compound: str = ""
    platforms: list[str] = Field(default_factory=list)
    publisher: str = ""
    localization: Localization = Field(default_factory=Localization)
    rating: float = 0
    info: list[str] = Field(default_factory=list)
    price: float = 0
    old_price: float = 0
    ps_price: float | None = None
    ea_price: float | None = None
    ps_plus: bool = False
    ea_access: bool = False
    discount: str = ""
    discount_end: datetime | None = None
    tags: set[str] = Field(default_factory=set)
