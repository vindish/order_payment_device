from app.repository.device_repo import DeviceRepository
from app.models.device import Device
from fastapi import HTTPException

class DeviceService:
    def __init__(self, db):
        self.repo = DeviceRepository(db)

    def create_device(self, sn: str):
        exist = self.repo.get_by_sn(sn)
        if exist:
            raise HTTPException(400, "设备已存在")

        device = Device(sn=sn)
        return self.repo.create(device)

    def list_devices(self):
        return self.repo.list()