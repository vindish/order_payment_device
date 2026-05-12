from datetime import datetime

from fastapi import HTTPException

from app.core.config import settings
from app.core.event_bus import publish
from app.core.idempotency import load_response, replay_or_reserve, store_response
from app.core.payment_signing import verify_payment_signature
from app.domain.enums import OrderStatus
from app.domain.order_flow import can_transfer
from app.repository.order_repo import OrderRepository


class PaymentService:
    def __init__(self, db):
        self.db = db
        self.repo = OrderRepository(db)

    def handle_callback(
        self,
        order_id: int,
        provider: str,
        trade_no: str | None,
        token: str | None,
        status: str,
        signature: str | None,
        idempotency_key: str | None = None,
    ):
        if settings.PAYMENT_SIGNING_SECRET and not verify_payment_signature(order_id, provider, trade_no, status, signature):
            if settings.PAYMENT_CALLBACK_TOKEN and token == settings.PAYMENT_CALLBACK_TOKEN:
                pass
            else:
                raise HTTPException(401, "Invalid payment callback signature")

        payload = {"order_id": order_id, "provider": provider, "trade_no": trade_no, "status": status}
        if status != OrderStatus.PAID.value:
            raise HTTPException(400, "Only PAID callbacks are supported")

        replay = replay_or_reserve(self.db, idempotency_key or trade_no, "payment_callback", payload)
        if replay and replay.response_body:
            return load_response(replay)

        order = self.repo.get_by_id_for_update(order_id)
        if not order:
            raise HTTPException(404, "Order not found")

        if order.status in {OrderStatus.PAID.value, OrderStatus.UNLOCKING.value, OrderStatus.DONE.value}:
            response = {"msg": "Duplicate callback ignored", "order_id": order.id, "status": order.status}
            store_response(self.db, idempotency_key or trade_no, response)
            self.db.commit()
            return response

        if not can_transfer(order.status, OrderStatus.PAID.value):
            raise HTTPException(400, "Invalid order state for payment callback")

        order.status = OrderStatus.PAID.value
        order.payment_provider = provider
        order.payment_trade_no = trade_no
        order.paid_at = datetime.utcnow()
        publish(self.db, "ORDER_PAID", {"order_id": order.id, "device_id": order.device_id}, "order", order.id)
        response = {"msg": "Payment accepted", "order_id": order.id, "status": order.status}
        store_response(self.db, idempotency_key or trade_no, response)
        self.db.commit()
        from app.tasks.device_tasks import dispatch_outbox_task

        dispatch_outbox_task.delay()
        return response
