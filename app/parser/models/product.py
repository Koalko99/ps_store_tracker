from typing import List, Set
from datetime import datetime
from pydantic import BaseModel

class Product(BaseModel):
    ID: str
    category: List[str]
    region: str
    product_type: str
    name: str
    origin_name: str
    editions: str
    description: str
    image: str
    compound: str
    platforms: List[str]
    publisher: str
    localization: List[str]
    rating: float
    ext_info: str
    price: float
    old_price: float
    ps_price: float
    ea_price: float
    ps_plus: bool
    ea_access: bool
    discount: int
    discount_end: datetime
    tags: Set[str]
