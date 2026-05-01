from app.repository.device_repo import DeviceRepository
from app.services.device_service import DeviceService

def handle_order_paid(db, payload):
    device_repo = DeviceRepository(db)
    device_service = DeviceService(db)

    device = device_repo.get_by_id(payload["device_id"])

    device_service.send_unlock(device, payload["order_id"])