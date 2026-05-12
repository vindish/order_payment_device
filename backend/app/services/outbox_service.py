import json
from datetime import datetime, timedelta

from sqlalchemy import or_

from app.models.messaging import DeadLetterEvent, OutboxEvent


class OutboxService:
    def __init__(self, db):
        self.db = db

    def enqueue(self, event_name: str, aggregate_type: str, aggregate_id: str | int, payload: dict) -> OutboxEvent:
        event = OutboxEvent(
            event_name=event_name,
            aggregate_type=aggregate_type,
            aggregate_id=str(aggregate_id),
            payload=json.dumps(payload, ensure_ascii=False, default=str),
        )
        self.db.add(event)
        return event

    def dispatch_due(self, limit: int = 50) -> int:
        now = datetime.utcnow()
        events = (
            self.db.query(OutboxEvent)
            .filter(
                OutboxEvent.status == "PENDING",
                OutboxEvent.next_attempt_at <= now,
                or_(OutboxEvent.locked_at.is_(None), OutboxEvent.locked_at < now - timedelta(minutes=5)),
            )
            .order_by(OutboxEvent.id.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
            .all()
        )

        dispatched = 0
        for event in events:
            event.locked_at = now
            try:
                payload = json.loads(event.payload)
                if event.event_name == "ORDER_PAID":
                    from app.tasks.device_tasks import handle_order_paid_task

                    handle_order_paid_task.delay(payload)
                event.status = "PUBLISHED"
                event.published_at = datetime.utcnow()
                event.error_message = None
                dispatched += 1
            except Exception as exc:
                event.retry_count += 1
                event.error_message = str(exc)
                event.locked_at = None
                event.next_attempt_at = datetime.utcnow() + timedelta(seconds=min(300, 2**event.retry_count))
                if event.retry_count >= 5:
                    event.status = "DEAD"
                    self.db.add(
                        DeadLetterEvent(
                            source=f"outbox:{event.event_name}",
                            payload=event.payload,
                            error_message=str(exc),
                            retry_count=event.retry_count,
                        )
                    )
        self.db.commit()
        return dispatched
