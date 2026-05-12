from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.schemas.order import OrderCreate, OrderOut
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return OrderService(db).create_order(user.id, data.device_sn, data.amount)


@router.get("", response_model=list[OrderOut])
def list_orders(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return OrderService(db).list_orders(user.id)
