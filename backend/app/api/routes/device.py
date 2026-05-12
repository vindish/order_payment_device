from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.schemas.device import DeviceCreate, DeviceOut
from app.services.device_service import DeviceService
from app.services.order_service import OrderService

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("", response_model=DeviceOut)
def create_device(
    data: DeviceCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return DeviceService(db).create_device(data.sn, data.name)


@router.get("", response_model=list[DeviceOut])
def list_devices(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return DeviceService(db).list_devices()


@router.post("/{sn}/heartbeat", response_model=DeviceOut)
def device_heartbeat(sn: str, db: Session = Depends(get_db)):
    return DeviceService(db).mark_heartbeat(sn)


@router.post("/events/unlocked")
def device_unlocked(order_id: int, db: Session = Depends(get_db)):
    return OrderService(db).update_status(order_id, "DONE")
