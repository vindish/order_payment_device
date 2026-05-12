from datetime import datetime

from fastapi import HTTPException

from app.core.config import settings
from app.core.event_bus import publish
from app.domain.enums import OrderStatus
from app.domain.order_flow import can_transfer
from app.repository.order_repo import OrderRepository


class PaymentService:
    def __init__(self, db):
        self.repo = OrderRepository(db)

    def handle_callback(self, order_id: int, provider: str, trade_no: str | None, token: str | None):
        if settings.PAYMENT_CALLBACK_TOKEN and token != settings.PAYMENT_CALLBACK_TOKEN:
            raise HTTPException(401, "Invalid payment callback token")

        order = self.repo.get_by_id(order_id)
        if not order:
            raise HTTPException(404, "Order not found")

        if order.status in {OrderStatus.PAID.value, OrderStatus.UNLOCKING.value, OrderStatus.DONE.value}:
            return {"msg": "Duplicate callback ignored", "order_id": order.id, "status": order.status}

        if not can_transfer(order.status, OrderStatus.PAID.value):
            raise HTTPException(400, "Invalid order state for payment callback")

        order.status = OrderStatus.PAID.value
        order.payment_provider = provider
        order.payment_trade_no = trade_no
        order.paid_at = datetime.utcnow()
        self.repo.update(order)

        publish("ORDER_PAID", {"order_id": order.id, "device_id": order.device_id})
        return {"msg": "Payment accepted", "order_id": order.id, "status": order.status}
