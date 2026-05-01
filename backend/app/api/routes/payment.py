from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payment", tags=["payment"])


@router.post("/callback")
def payment_callback(
    order_id: int,
    db: Session = Depends(get_db)
):
    service = PaymentService(db)
    return service.handle_callback(order_id)