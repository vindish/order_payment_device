from app.domain.enums import OrderStatus


ORDER_FLOW = {
    OrderStatus.INIT: {OrderStatus.PAID, OrderStatus.CANCELED},
    OrderStatus.PAID: {OrderStatus.UNLOCKING, OrderStatus.FAILED},
    OrderStatus.UNLOCKING: {OrderStatus.DONE, OrderStatus.FAILED},
    OrderStatus.FAILED: {OrderStatus.UNLOCKING, OrderStatus.CANCELED},
    OrderStatus.DONE: set(),
    OrderStatus.CANCELED: set(),
}


def can_transfer(old: str, new: str) -> bool:
    try:
        old_status = OrderStatus(old)
        new_status = OrderStatus(new)
    except ValueError:
        return False
    return new_status in ORDER_FLOW.get(old_status, set())
