from fastapi import HTTPException
from app.repository.order_repo import OrderRepository
from app.domain.enums import OrderStatus
from app.domain.order_flow import can_transfer
from app.core.event_bus import publish


class PaymentService:
    def __init__(self, db):
        self.repo = OrderRepository(db)

    def handle_callback(self, order_id: int):
        order = self.repo.get_by_id(order_id)

        if not order:
            raise HTTPException(404, "订单不存在")

        # ✅ 幂等
        if order.status == OrderStatus.PAID:
            return {"msg": "重复回调已忽略"}

        # ✅ 状态机
        if not can_transfer(order.status, OrderStatus.PAID):
            raise HTTPException(400, "非法状态流转")

        # ✅ 更新订单
        order.status = OrderStatus.PAID
        self.repo.update(order)

        # ✅ 发布事件（关键）
        publish("ORDER_PAID", {
            "order_id": order.id,
            "device_id": order.device_id
        })

        return {"msg": "支付成功（异步开锁）"}