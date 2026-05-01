from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.services.order_service import OrderService
from app.schemas.order import OrderCreate, OrderOut

router = APIRouter(prefix="/order", tags=["order"])


# ✅ 创建订单
@router.post("", response_model=OrderOut)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    service = OrderService(db)
    return service.create_order(user.id, data.device_sn)


# ✅ 查询当前用户订单
@router.get("", response_model=list[OrderOut])
def list_orders(
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    service = OrderService(db)
    return service.list_orders(user.id)