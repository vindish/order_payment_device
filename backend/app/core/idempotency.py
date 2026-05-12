import hashlib
import json

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.security import IdempotencyKey


def request_hash(payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def replay_or_reserve(db, key: str | None, scope: str, payload: dict):
    if not key:
        return None

    digest = request_hash(payload)
    existing = db.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
    if existing:
        if existing.scope != scope or existing.request_hash != digest:
            raise HTTPException(409, "Idempotency key reused with different request")
        return existing

    record = IdempotencyKey(key=key, scope=scope, request_hash=digest)
    db.add(record)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return db.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
    return None


def store_response(db, key: str | None, response: dict, status_code: int = 200) -> None:
    if not key:
        return
    record = db.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
    if not record:
        return
    record.response_body = json.dumps(response, ensure_ascii=False, default=str)
    record.status_code = status_code


def load_response(record) -> dict | None:
    if not record or not record.response_body:
        return None
    return json.loads(record.response_body)
