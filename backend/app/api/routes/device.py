from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.services.device_service import DeviceService
from app.schemas.device import DeviceCreate, DeviceOut
from app.services.order_service import OrderService

router = APIRouter(prefix="/device", tags=["device"])


@router.post("", response_model=DeviceOut)
def create_device(
    data: DeviceCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)  # 🔥必须登录
):
    service = DeviceService(db)
    return service.create_device(data.sn)


@router.get("", response_model=list[DeviceOut])
def list_devices(
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    service = DeviceService(db)
    return service.list_devices()


@router.post("/event")
def device_event(
    order_id: int,
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    return service.update_status(order_id, "DONE")