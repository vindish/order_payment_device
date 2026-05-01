from fastapi import HTTPException

from app.repository.order_repo import OrderRepository
from app.repository.device_repo import DeviceRepository
from app.models.order import Order
from app.domain.enums import OrderStatus
from app.domain.order_flow import can_transfer


class OrderService:
    def __init__(self, db):
        self.repo = OrderRepository(db)
        self.device_repo = DeviceRepository(db)

    # ✅ 创建订单
    def create_order(self, user_id: int, device_sn: str):
        device = self.device_repo.get_by_sn(device_sn)
        if not device:
            raise HTTPException(404, "设备不存在")

        order = Order(
            user_id=user_id,
            device_id=device.id,
            status=OrderStatus.INIT
        )

        return self.repo.create(order)

    # ✅ 查询当前用户订单
    def list_orders(self, user_id: int):
        return self.repo.list_by_user(user_id)

    # ✅ 状态流转（后面支付/MQTT用）
    def update_status(self, order_id: int, new_status: str):
        order = self.repo.get_by_id(order_id)
        if not order:
            raise HTTPException(404, "订单不存在")

        if not can_transfer(order.status, new_status):
            raise HTTPException(400, f"非法状态流转 {order.status} → {new_status}")

        order.status = new_status
        return self.repo.update(order)