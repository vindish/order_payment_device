import json

from app.core.config import settings
from app.core.security import verify_signature


def canonical_payment_payload(order_id: int, provider: str, trade_no: str | None, status: str) -> bytes:
    payload = {
        "order_id": order_id,
        "provider": provider,
        "status": status,
        "trade_no": trade_no,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verify_payment_signature(order_id: int, provider: str, trade_no: str | None, status: str, signature: str | None) -> bool:
    payload = canonical_payment_payload(order_id, provider, trade_no, status)
    return verify_signature(settings.PAYMENT_SIGNING_SECRET, payload, signature)
