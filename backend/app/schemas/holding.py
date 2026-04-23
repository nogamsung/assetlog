from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.holding import AssetType


class HoldingBase(BaseModel):
    asset_type: AssetType
    symbol: str
    quantity: float
    avg_cost: float
    purchased_at: datetime


class HoldingCreate(HoldingBase):
    pass


class HoldingRead(HoldingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
