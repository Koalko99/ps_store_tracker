from pydantic import BaseModel
from typing import List

class PlaystationPlus(BaseModel):
    region: str
    essential: List[str]
    extra: List[str]
    premium: List[str]
