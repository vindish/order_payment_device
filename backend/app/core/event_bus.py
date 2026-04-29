# app/core/event_bus.py
from app.tasks.device_tasks import handle_order_paid_task

def publish(event_name: str, payload: dict):
    if event_name == "ORDER_PAID":
        handle_order_paid_task.delay(payload)

# def publish(event_name: str, payload: dict):
#     print(f"[EVENT] {event_name} {payload}")