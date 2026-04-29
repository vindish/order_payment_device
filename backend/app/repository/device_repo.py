from app.models.device import Device

class DeviceRepository:
    def __init__(self, db):
        self.db = db

    def create(self, device: Device):
        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)
        return device

    def list(self):
        return self.db.query(Device).all()

    def get_by_sn(self, sn: str):
        return self.db.query(Device).filter(Device.sn == sn).first()
    
    def get_by_id(self, device_id: int):
        return self.db.query(Device).filter(Device.id == device_id).first()