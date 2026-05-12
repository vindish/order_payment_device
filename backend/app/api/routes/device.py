from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.rbac import Role, require_min_role
from app.deps import get_current_device, get_current_user, get_db
from app.schemas.device import (
    DeviceCommandAckIn,
    DeviceCommandIn,
    DeviceCreate,
    DeviceCredentialOut,
    DeviceOut,
    DeviceShadowIn,
    DeviceShadowOut,
    TelemetryIn,
)
from app.services.device_service import DeviceService
from app.services.order_service import OrderService

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("", response_model=DeviceCredentialOut)
def create_device(
    data: DeviceCreate,
    db: Session = Depends(get_db),
    user=Depends(require_min_role(Role.OPERATOR)),
):
    return DeviceService(db).create_device(data.sn, data.name)


@router.get("", response_model=list[DeviceOut])
def list_devices(
    db: Session = Depends(get_db),
    user=Depends(require_min_role(Role.OPERATOR)),
):
    return DeviceService(db).list_devices()


@router.post("/{sn}/heartbeat", response_model=DeviceOut)
def device_heartbeat(sn: str, db: Session = Depends(get_db), device=Depends(get_current_device)):
    if device.sn != sn:
        raise HTTPException(403, "Device SN mismatch")
    return DeviceService(db).mark_heartbeat(device)


@router.post("/events/unlocked")
def device_unlocked(order_id: int, db: Session = Depends(get_db), device=Depends(get_current_device)):
    return OrderService(db).update_status(order_id, "DONE")


@router.get("/{sn}/shadow", response_model=DeviceShadowOut)
def get_shadow(sn: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    device = DeviceService(db).repo.get_by_sn(sn)
    if not device:
        raise HTTPException(404, "Device not found")
    return DeviceService(db).get_shadow(device)


@router.put("/{sn}/shadow", response_model=DeviceShadowOut)
def update_shadow(
    sn: str,
    data: DeviceShadowIn,
    db: Session = Depends(get_db),
    user=Depends(require_min_role(Role.OPERATOR)),
):
    device = DeviceService(db).repo.get_by_sn(sn)
    if not device:
        raise HTTPException(404, "Device not found")
    return DeviceService(db).update_shadow(device, data.desired_state, data.reported_state)


@router.post("/{sn}/commands")
def issue_command(
    sn: str,
    data: DeviceCommandIn,
    db: Session = Depends(get_db),
    user=Depends(require_min_role(Role.OPERATOR)),
):
    device = DeviceService(db).repo.get_by_sn(sn)
    if not device:
        raise HTTPException(404, "Device not found")
    command = DeviceService(db).issue_command(device, data.command, data.payload, data.idempotency_key)
    return {"id": command.id, "status": command.status}


@router.post("/commands/ack")
def ack_command(data: DeviceCommandAckIn, db: Session = Depends(get_db), device=Depends(get_current_device)):
    return DeviceService(db).ack_command(device, data.command_id, data.status, data.error_message)


@router.post("/telemetry")
def telemetry(data: TelemetryIn, db: Session = Depends(get_db), device=Depends(get_current_device)):
    return DeviceService(db).record_telemetry(device, data.metric, data.value, data.unit, data.recorded_at)
