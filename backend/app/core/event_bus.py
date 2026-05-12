from app.services.outbox_service import OutboxService


def publish(db, event_name: str, payload: dict, aggregate_type: str, aggregate_id: str | int):
    return OutboxService(db).enqueue(event_name, aggregate_type, aggregate_id, payload)
