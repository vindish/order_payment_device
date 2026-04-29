from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.repository.device_repo import DeviceRepository
from app.services.device_service import DeviceService


@celery_app.task
def handle_order_paid_task(payload):
    db = SessionLocal()

    try:
        device_repo = DeviceRepository(db)
        device_service = DeviceService(db)

        device = device_repo.get_by_id(payload["device_id"])

        device_service.send_unlock(device, payload["order_id"])

    finally:
        db.close()