"""Payment callback signature utilities.

This module supports three modes:

* ``manual``  : Internal HMAC-SHA256 signing for testing or trusted relays.
                Used by ``/payments/callback``.
* ``wechat``  : WeChat Pay APIv3 - RSA-SHA256 over ``timestamp\\nnonce\\nbody\\n``
                using the WeChat platform certificate public key, plus AES-GCM
                decryption of the ``resource`` payload with the APIv3 key.
* ``alipay``  : Alipay open API - RSA2 (RSA-SHA256) over the asynchronous
                notification form parameters using the Alipay public key.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings
from app.core.security import verify_signature

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Manual / internal HMAC mode
# ---------------------------------------------------------------------------


def canonical_payment_payload(
    order_id: int,
    provider: str,
    trade_no: str | None,
    status: str,
) -> bytes:
    payload = {
        "order_id": order_id,
        "provider": provider,
        "status": status,
        "trade_no": trade_no,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verify_payment_signature(
    order_id: int,
    provider: str,
    trade_no: str | None,
    status: str,
    signature: str | None,
) -> bool:
    payload = canonical_payment_payload(order_id, provider, trade_no, status)
    return verify_signature(settings.PAYMENT_SIGNING_SECRET, payload, signature)


# ---------------------------------------------------------------------------
# out_trade_no <-> order_id mapping
# ---------------------------------------------------------------------------


def build_out_trade_no(order_id: int, suffix: str | None = None) -> str:
    """Compose an out_trade_no acceptable by WeChat/Alipay.

    The convention is ``{prefix}{order_id}`` with an optional ``-{suffix}``
    that the merchant can use to disambiguate retries. Both providers limit
    out_trade_no length so keep the prefix short.
    """
    base = f"{settings.OUT_TRADE_NO_PREFIX}{order_id}"
    return f"{base}-{suffix}" if suffix else base


def parse_order_id_from_out_trade_no(out_trade_no: str | None) -> int | None:
    if not out_trade_no:
        return None
    prefix = settings.OUT_TRADE_NO_PREFIX
    raw = out_trade_no[len(prefix):] if prefix and out_trade_no.startswith(prefix) else out_trade_no
    head = raw.split("-", 1)[0]
    try:
        return int(head)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Key loading helpers
# ---------------------------------------------------------------------------


def _normalize_pem(value: str | None, kind: str = "PUBLIC KEY") -> bytes | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if "BEGIN" in text:
        return text.encode("utf-8")
    # Tolerate raw base64 keys (common for Alipay configs).
    body = "\n".join(text[i : i + 64] for i in range(0, len(text), 64))
    return f"-----BEGIN {kind}-----\n{body}\n-----END {kind}-----\n".encode("utf-8")


def _load_public_key(pem_value: str | None):
    pem = _normalize_pem(pem_value, "PUBLIC KEY")
    if not pem:
        return None
    return serialization.load_pem_public_key(pem)


# ---------------------------------------------------------------------------
# WeChat Pay APIv3
# ---------------------------------------------------------------------------


def verify_wechat_v3_signature(
    timestamp: str,
    nonce: str,
    body: str,
    signature_b64: str,
) -> bool:
    """Verify a WeChat Pay APIv3 callback signature."""

    public_key = _load_public_key(settings.WECHAT_PAY_PUBLIC_KEY)
    if public_key is None:
        logger.error("WECHAT_PAY_PUBLIC_KEY is not configured")
        return False
    if not (timestamp and nonce and signature_b64):
        return False

    message = f"{timestamp}\n{nonce}\n{body}\n".encode("utf-8")
    try:
        signature = base64.b64decode(signature_b64)
        public_key.verify(signature, message, padding.PKCS1v15(), hashes.SHA256())
        return True
    except (InvalidSignature, ValueError, TypeError) as exc:
        logger.warning("WeChat v3 signature verification failed: %s", exc)
        return False


def decrypt_wechat_resource(resource: Mapping[str, Any]) -> dict[str, Any]:
    """Decrypt the AES-GCM ``resource`` field of a WeChat Pay APIv3 callback."""

    api_v3_key = settings.WECHAT_PAY_API_V3_KEY
    if not api_v3_key:
        raise ValueError("WECHAT_PAY_API_V3_KEY is not configured")

    algorithm = resource.get("algorithm", "AEAD_AES_256_GCM")
    if algorithm != "AEAD_AES_256_GCM":
        raise ValueError(f"Unsupported WeChat resource algorithm: {algorithm}")

    nonce = resource.get("nonce", "").encode("utf-8")
    associated_data = resource.get("associated_data", "").encode("utf-8")
    ciphertext = base64.b64decode(resource.get("ciphertext", ""))

    aes = AESGCM(api_v3_key.encode("utf-8"))
    plaintext = aes.decrypt(nonce, ciphertext, associated_data)
    return json.loads(plaintext.decode("utf-8"))


# ---------------------------------------------------------------------------
# Alipay open API
# ---------------------------------------------------------------------------


# Alipay async notifications send these fields in addition to the signed body;
# they must be excluded from the signature input.
_ALIPAY_SIGN_EXCLUDE = {"sign", "sign_type"}


def _alipay_sign_string(params: Mapping[str, Any]) -> bytes:
    pairs = []
    for key in sorted(params.keys()):
        if key in _ALIPAY_SIGN_EXCLUDE:
            continue
        value = params[key]
        if value is None or value == "":
            continue
        pairs.append(f"{key}={value}")
    return "&".join(pairs).encode("utf-8")


def verify_alipay_signature(params: Mapping[str, Any]) -> bool:
    """Verify the signature on an Alipay asynchronous notification."""

    public_key = _load_public_key(settings.ALIPAY_PUBLIC_KEY)
    if public_key is None:
        logger.error("ALIPAY_PUBLIC_KEY is not configured")
        return False

    signature_b64 = params.get("sign")
    sign_type = (params.get("sign_type") or "RSA2").upper()
    if not signature_b64:
        return False

    message = _alipay_sign_string(params)
    try:
        signature = base64.b64decode(signature_b64)
        if sign_type == "RSA2":
            public_key.verify(signature, message, padding.PKCS1v15(), hashes.SHA256())
        elif sign_type == "RSA":
            public_key.verify(signature, message, padding.PKCS1v15(), hashes.SHA1())
        else:
            logger.warning("Unsupported Alipay sign_type: %s", sign_type)
            return False
        return True
    except (InvalidSignature, ValueError, TypeError) as exc:
        logger.warning("Alipay signature verification failed: %s", exc)
        return False
