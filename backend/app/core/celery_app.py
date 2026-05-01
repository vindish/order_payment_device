from celery import Celery
from app.core.config import settings


celery_app = Celery(
    "app",
    broker=f"redis://{settings.REDIS_HOST}:6379/0",
    backend=f"redis://{settings.REDIS_HOST}:6379/0"
)

# 👇 加这一行（关键）
import app.tasks.device_tasks
celery_app.autodiscover_tasks(["app.tasks"])

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
)