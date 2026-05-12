from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException

from app.core.idempotency import load_response, replay_or_reserve, store_response
from app.domain.enums import OrderStatus
from app.domain.order_flow import can_transfer
from app.models.order import Order
from app.repository.device_repo import DeviceRepository
from app.repository.order_repo import OrderRepository


class OrderService:
    def __init__(self, db):
        self.repo = OrderRepository(db)
        self.device_repo = DeviceRepository(db)

    def create_order(
        self,
        user_id: int,
        device_sn: str,
        amount: Decimal = Decimal("0.00"),
        idempotency_key: str | None = None,
    ):
        replay = replay_or_reserve(
            self.repo.db,
            idempotency_key,
            "create_order",
            {"user_id": user_id, "device_sn": device_sn, "amount": str(amount)},
        )
        if replay and replay.response_body:
            response = load_response(replay)
            return self.repo.get_by_id(int(response["order_id"]))

        device = self.device_repo.get_by_sn(device_sn)
        if not device:
            raise HTTPException(404, "Device not found")

        order = Order(
            user_id=user_id,
            device_id=device.id,
            amount=amount,
            status=OrderStatus.INIT.value,
        )
        created = self.repo.create(order)
        store_response(self.repo.db, idempotency_key, {"order_id": created.id})
        self.repo.db.commit()
        return created

    def list_orders(self, user_id: int):
        return self.repo.list_by_user(user_id)

    def update_status(self, order_id: int, new_status: str, error_message: str | None = None):
        order = self.repo.get_by_id_for_update(order_id)
        if not order:
            raise HTTPException(404, "Order not found")

        if not can_transfer(order.status, new_status):
            raise HTTPException(400, f"Invalid state transition: {order.status} -> {new_status}")

        order.status = new_status
        order.error_message = error_message
        if new_status == OrderStatus.DONE.value:
            order.unlocked_at = datetime.utcnow()
        return self.repo.update(order)
