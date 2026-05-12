from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.domain.enums import OrderStatus
from app.repository.device_repo import DeviceRepository
from app.repository.order_repo import OrderRepository
from app.services.device_service import DeviceService


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def handle_order_paid_task(self, payload):
    db = SessionLocal()
    try:
        order_repo = OrderRepository(db)
        device_repo = DeviceRepository(db)
        device_service = DeviceService(db)

        order = order_repo.get_by_id(payload["order_id"])
        if not order:
            raise ValueError("Order not found")

        if order.status == OrderStatus.DONE.value:
            return {"status": "already_done", "order_id": order.id}

        order.status = OrderStatus.UNLOCKING.value
        order.retry_count = self.request.retries
        order_repo.update(order)

        device = device_repo.get_by_id(order.device_id)
        if not device:
            raise ValueError("Device not found")

        device_service.send_unlock(device, order.id)
        return {"status": "sent", "order_id": order.id, "device_sn": device.sn}
    except Exception as exc:
        db.rollback()
        order_id = payload.get("order_id") if isinstance(payload, dict) else None
        if order_id:
            order = OrderRepository(db).get_by_id(order_id)
            if order:
                order.retry_count = self.request.retries
                order.error_message = str(exc)
                if self.request.retries >= 5:
                    order.status = OrderStatus.FAILED.value
                db.commit()
        raise
    finally:
        db.close()
