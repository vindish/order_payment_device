import json
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException

from app.core import mqtt
from app.core.security import create_device_secret
from app.domain.enums import DeviceStatus
from app.models.device import Device
from app.models.iot import DeviceCommand, DeviceShadow, TelemetryPoint
from app.repository.device_repo import DeviceRepository


class DeviceService:
    def __init__(self, db):
        self.repo = DeviceRepository(db)
        self.db = db

    def create_device(self, sn: str, name: str | None = None):
        if self.repo.get_by_sn(sn):
            raise HTTPException(400, "Device already exists")

        secret, secret_hash = create_device_secret()
        device = Device(sn=sn, name=name, secret_hash=secret_hash)
        created = self.repo.create(device)
        created.device_secret = secret
        return created

    def list_devices(self):
        return self.repo.list()

    def mark_heartbeat(self, device_or_sn):
        device = device_or_sn if isinstance(device_or_sn, Device) else self.repo.get_by_sn(device_or_sn)
        if not device:
            raise HTTPException(404, "Device not found")
        device.status = DeviceStatus.ONLINE.value
        device.last_seen_at = datetime.utcnow()
        return self.repo.update(device)

    def send_unlock(self, device, order_id: int):
        return self.issue_command(device, "unlock", {"order_id": order_id}, f"unlock:{order_id}")

    def issue_command(
        self,
        device,
        command: str,
        payload: dict,
        idempotency_key: str | None = None,
    ):
        key = idempotency_key or str(uuid4())
        existing = self.db.query(DeviceCommand).filter(DeviceCommand.idempotency_key == key).first()
        if existing:
            return existing

        record = DeviceCommand(
            device_id=device.id,
            command=command,
            payload=json.dumps(payload, ensure_ascii=False, default=str),
            idempotency_key=key,
        )
        self.db.add(record)
        self.db.flush()
        mqtt.publish(f"device/{device.sn}/cmd", {"command_id": record.id, "cmd": command, "payload": payload})
        record.status = "SENT"
        record.sent_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(record)
        return record

    def ack_command(self, device, command_id: int, status: str, error_message: str | None = None):
        command = (
            self.db.query(DeviceCommand)
            .filter(DeviceCommand.id == command_id, DeviceCommand.device_id == device.id)
            .with_for_update()
            .first()
        )
        if not command:
            raise HTTPException(404, "Command not found")
        command.status = status
        command.error_message = error_message
        command.acked_at = datetime.utcnow()
        self.db.commit()
        return {"msg": "ack accepted", "command_id": command.id, "status": command.status}

    def get_shadow(self, device):
        shadow = self.db.query(DeviceShadow).filter(DeviceShadow.device_id == device.id).first()
        if not shadow:
            shadow = DeviceShadow(device_id=device.id)
            self.db.add(shadow)
            self.db.commit()
            self.db.refresh(shadow)
        return self._shadow_out(shadow)

    def update_shadow(self, device, desired_state: dict | None = None, reported_state: dict | None = None):
        shadow = self.db.query(DeviceShadow).filter(DeviceShadow.device_id == device.id).with_for_update().first()
        if not shadow:
            shadow = DeviceShadow(device_id=device.id)
            self.db.add(shadow)
            self.db.flush()
        if desired_state is not None:
            shadow.desired_state = json.dumps(desired_state, ensure_ascii=False)
        if reported_state is not None:
            shadow.reported_state = json.dumps(reported_state, ensure_ascii=False)
        shadow.version += 1
        shadow.updated_at = datetime.utcnow()
        self.db.commit()
        return self._shadow_out(shadow)

    def record_telemetry(self, device, metric: str, value, unit: str | None = None, recorded_at=None):
        point = TelemetryPoint(
            device_id=device.id,
            metric=metric,
            value=value,
            unit=unit,
            recorded_at=recorded_at or datetime.utcnow(),
        )
        self.db.add(point)
        device.last_seen_at = datetime.utcnow()
        device.status = DeviceStatus.ONLINE.value
        self.db.commit()
        return {"msg": "telemetry accepted", "device_id": device.id, "metric": metric}

    def _shadow_out(self, shadow):
        return {
            "device_id": shadow.device_id,
            "desired_state": json.loads(shadow.desired_state or "{}"),
            "reported_state": json.loads(shadow.reported_state or "{}"),
            "version": shadow.version,
        }
