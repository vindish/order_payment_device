from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "app",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.device_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    task_routes={
        "app.tasks.device_tasks.handle_order_paid_task": {"queue": "device_commands"},
        "app.tasks.device_tasks.dispatch_outbox_task": {"queue": "outbox"},
    },
    task_reject_on_worker_lost=True,
    task_default_retry_delay=10,
)

celery_app.conf.beat_schedule = {
    "dispatch-outbox-every-5s": {
        "task": "app.tasks.device_tasks.dispatch_outbox_task",
        "schedule": 5.0,
    }
}
