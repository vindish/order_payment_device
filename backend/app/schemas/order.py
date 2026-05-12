from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    device_sn: str
    amount: Decimal = Field(default=Decimal("0.00"), ge=0)


class OrderOut(BaseModel):
    id: int
    user_id: int
    device_id: int
    amount: Decimal
    currency: str
    status: str
    retry_count: int
    created_at: datetime

    class Config:
        from_attributes = True
