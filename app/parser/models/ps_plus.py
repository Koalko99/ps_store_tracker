from pydantic import BaseModel, ConfigDict


class PsPlusGame(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    product_id: str


class PlaystationPlus(BaseModel):
    region: str
    essential: list[PsPlusGame]
    extra: list[PsPlusGame]
    premium: list[PsPlusGame]
