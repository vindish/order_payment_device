from pydantic import BaseModel


class PaymentCallbackIn(BaseModel):
    order_id: int
    provider: str = "manual"
    trade_no: str | None = None
    token: str | None = None
