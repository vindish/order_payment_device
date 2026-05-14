"""Payment callback orchestration.

Three providers are supported:

* ``manual``  - HMAC-signed callback issued by trusted internal tooling or
                tests. Backwards compatible with the original implementation.
* ``wechat``  - WeChat Pay APIv3 asynchronous notification. Verified with the
                platform certificate public key. Resource payload is decrypted
                with the APIv3 key.
* ``alipay``  - Alipay async notification. Verified with the Alipay public key
                using RSA2 over the form-encoded parameters.

All three paths converge on :meth:`_apply_paid_transition`, which performs the
state transition under a row lock, idempotency replay protection, and an
outbox enqueue for the device unlock command.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Mapping

from fastapi import HTTPException

from app.core.config import settings
from app.core.event_bus import publish
from app.core.idempotency import load_response, replay_or_reserve, store_response
from app.core.payment_signing import (
    decrypt_wechat_resource,
    parse_order_id_from_out_trade_no,
    verify_alipay_signature,
    verify_payment_signature,
    verify_wechat_v3_signature,
)
from app.domain.enums import OrderStatus
from app.domain.order_flow import can_transfer
from app.repository.order_repo import OrderRepository

logger = logging.getLogger(__name__)


# Alipay trade_status values that mean "money received".
_ALIPAY_PAID_STATUS = {"TRADE_SUCCESS", "TRADE_FINISHED"}

# WeChat Pay APIv3 resource trade_state values that mean "money received".
_WECHAT_PAID_STATUS = {"SUCCESS"}


class PaymentService:
    def __init__(self, db):
        self.db = db
        self.repo = OrderRepository(db)

    # ------------------------------------------------------------------
    # Manual / internal HMAC callback (kept for tooling and tests)
    # ------------------------------------------------------------------

    def handle_callback(
        self,
        order_id: int,
        provider: str,
        trade_no: str | None,
        token: str | None,
        status: str,
        signature: str | None,
        idempotency_key: str | None = None,
    ):
        signing_secret = settings.PAYMENT_SIGNING_SECRET
        callback_token = settings.PAYMENT_CALLBACK_TOKEN

        signature_ok = bool(signing_secret) and verify_payment_signature(
            order_id, provider, trade_no, status, signature
        )
        token_ok = bool(callback_token) and token == callback_token

        if not signature_ok and not token_ok:
            raise HTTPException(401, "Invalid payment callback signature")

        if status != OrderStatus.PAID.value:
            raise HTTPException(400, "Only PAID callbacks are supported")

        return self._apply_paid_transition(
            order_id=order_id,
            provider=provider,
            trade_no=trade_no,
            idempotency_key=idempotency_key or trade_no,
        )

    # ------------------------------------------------------------------
    # WeChat Pay APIv3 callback
    # ------------------------------------------------------------------

    def handle_wechat_callback(
        self,
        *,
        timestamp: str,
        nonce: str,
        signature: str,
        body: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not verify_wechat_v3_signature(timestamp, nonce, body, signature):
            raise HTTPException(401, "Invalid WeChat Pay signature")

        try:
            envelope = json.loads(body)
        except json.JSONDecodeError as exc:
            raise HTTPException(400, "Malformed WeChat callback body") from exc

        if envelope.get("event_type") and "TRANSACTION.SUCCESS" not in envelope["event_type"]:
            # Non-success events should still be acknowledged but not processed.
            return {"code": "SUCCESS", "message": "ignored"}

        resource = envelope.get("resource") or {}
        try:
            decrypted = decrypt_wechat_resource(resource)
        except Exception as exc:  # noqa: BLE001 - wrap any crypto failure
            logger.exception("WeChat resource decryption failed")
            raise HTTPException(400, "Failed to decrypt WeChat resource") from exc

        trade_state = decrypted.get("trade_state")
        if trade_state not in _WECHAT_PAID_STATUS:
            return {"code": "SUCCESS", "message": f"ignored:{trade_state}"}

        out_trade_no = decrypted.get("out_trade_no")
        order_id = parse_order_id_from_out_trade_no(out_trade_no)
        if not order_id:
            raise HTTPException(400, "Missing or invalid out_trade_no in WeChat callback")

        trade_no = decrypted.get("transaction_id") or out_trade_no

        self._apply_paid_transition(
            order_id=order_id,
            provider="wechat",
            trade_no=trade_no,
            idempotency_key=idempotency_key or trade_no,
            extra={"out_trade_no": out_trade_no},
        )
        # WeChat expects a JSON envelope with code=SUCCESS to stop retries.
        return {"code": "SUCCESS", "message": "OK"}

    # ------------------------------------------------------------------
    # Alipay async notification
    # ------------------------------------------------------------------

    def handle_alipay_callback(
        self,
        params: Mapping[str, Any],
        idempotency_key: str | None = None,
    ) -> str:
        if not verify_alipay_signature(params):
            raise HTTPException(401, "Invalid Alipay signature")

        if settings.ALIPAY_APP_ID and params.get("app_id") != settings.ALIPAY_APP_ID:
            raise HTTPException(401, "Alipay app_id mismatch")

        trade_status = params.get("trade_status")
        if trade_status not in _ALIPAY_PAID_STATUS:
            # Alipay only stops retrying when the merchant returns ``success``.
            return "success"

        out_trade_no = params.get("out_trade_no")
        order_id = parse_order_id_from_out_trade_no(out_trade_no)
        if not order_id:
            raise HTTPException(400, "Missing or invalid out_trade_no in Alipay callback")

        trade_no = params.get("trade_no") or out_trade_no

        self._apply_paid_transition(
            order_id=order_id,
            provider="alipay",
            trade_no=trade_no,
            idempotency_key=idempotency_key or trade_no,
            extra={"out_trade_no": out_trade_no},
        )
        # Alipay expects the literal string ``success``.
        return "success"

    # ------------------------------------------------------------------
    # Shared transition logic
    # ------------------------------------------------------------------

    def _apply_paid_transition(
        self,
        *,
        order_id: int,
        provider: str,
        trade_no: str | None,
        idempotency_key: str | None,
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "order_id": order_id,
            "provider": provider,
            "trade_no": trade_no,
            "status": OrderStatus.PAID.value,
        }
        if extra:
            payload.update(extra)

        replay = replay_or_reserve(self.db, idempotency_key, "payment_callback", payload)
        if replay and replay.response_body:
            return load_response(replay) or {}

        order = self.repo.get_by_id_for_update(order_id)
        if not order:
            raise HTTPException(404, "Order not found")

        if order.status in {OrderStatus.PAID.value, OrderStatus.UNLOCKING.value, OrderStatus.DONE.value}:
            response = {"msg": "Duplicate callback ignored", "order_id": order.id, "status": order.status}
            store_response(self.db, idempotency_key, response)
            self.db.commit()
            return response

        if not can_transfer(order.status, OrderStatus.PAID.value):
            raise HTTPException(400, "Invalid order state for payment callback")

        order.status = OrderStatus.PAID.value
        order.payment_provider = provider
        order.payment_trade_no = trade_no
        order.paid_at = datetime.utcnow()

        publish(
            self.db,
            "ORDER_PAID",
            {"order_id": order.id, "device_id": order.device_id, "provider": provider},
            "order",
            order.id,
        )

        response = {"msg": "Payment accepted", "order_id": order.id, "status": order.status}
        store_response(self.db, idempotency_key, response)
        self.db.commit()

        # Fire the outbox dispatcher so the device receives the unlock command
        # without waiting for the next beat tick.
        try:
            from app.tasks.device_tasks import dispatch_outbox_task

            dispatch_outbox_task.delay()
        except Exception:  # noqa: BLE001 - never let a worker hiccup fail the callback
            logger.exception("Failed to enqueue dispatch_outbox_task")

        return response
