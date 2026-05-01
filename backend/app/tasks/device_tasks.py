from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.repository.device_repo import DeviceRepository
from app.services.device_service import DeviceService
from app.repository.order_repo import OrderRepository

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=3, retry_kwargs={"max_retries": 3})
def handle_order_paid_task(self, payload):
    db = SessionLocal()

    try:
        device_repo = DeviceRepository(db)
        device_service = DeviceService(db)

        order_repo = OrderRepository(db)
        order = order_repo.get_by_id(payload["order_id"])

        device = device_repo.get_by_id(order.device_id)

        # device = device_repo.get_by_id(payload["device_id"])

        if not device:
            raise Exception("设备不存在")

        device_service.send_unlock(device, payload["order_id"])
        print("TASK RUNNING:", payload)
        order.status = "DONE"
        db.commit()
    finally:
        db.close()