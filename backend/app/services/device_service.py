from datetime import datetime

from fastapi import HTTPException

from app.core import mqtt
from app.domain.enums import DeviceStatus
from app.models.device import Device
from app.repository.device_repo import DeviceRepository


class DeviceService:
    def __init__(self, db):
        self.repo = DeviceRepository(db)
        self.db = db

    def create_device(self, sn: str, name: str | None = None):
        if self.repo.get_by_sn(sn):
            raise HTTPException(400, "Device already exists")

        device = Device(sn=sn, name=name)
        return self.repo.create(device)

    def list_devices(self):
        return self.repo.list()

    def mark_heartbeat(self, sn: str):
        device = self.repo.get_by_sn(sn)
        if not device:
            device = self.repo.create(Device(sn=sn, status=DeviceStatus.ONLINE.value))
        device.status = DeviceStatus.ONLINE.value
        device.last_seen_at = datetime.utcnow()
        return self.repo.update(device)

    def send_unlock(self, device, order_id: int):
        topic = f"device/{device.sn}/cmd"
        mqtt.publish(topic, {"cmd": "unlock", "order_id": order_id})
