from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas.payment import PaymentCallbackIn
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/callback")
def payment_callback(
    data: PaymentCallbackIn,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    return PaymentService(db).handle_callback(
        order_id=data.order_id,
        provider=data.provider,
        trade_no=data.trade_no,
        token=data.token,
        status=data.status,
        signature=data.signature,
        idempotency_key=idempotency_key,
    )
