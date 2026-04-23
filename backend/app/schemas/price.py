from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PriceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    asset_type: str
    price: float
    currency: str
    fetched_at: datetime
