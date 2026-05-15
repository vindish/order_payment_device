"""MQTT publisher with lazy connect and reconnect.

The original implementation connected to the broker at import time. That
caused two problems:

* When the backend container starts before Mosquitto is ready, the import
  fails silently into ``MOCK`` mode and never publishes again until the
  process is restarted.
* The TCP socket was inherited by Celery workers when they fork, leaving the
  child with a half-open connection that paho cannot recover from.

This module now defers the connection, performs it inside the calling
process, and lazily reconnects on failure. ``publish`` always succeeds from
the caller's point of view: if the broker is unreachable the payload is
logged as ``MOCK MQTT`` so the rest of the pipeline (outbox + Celery) can
keep running and surface the failure in a higher-level retry.
"""

from __future__ import annotations

import json
import logging
import os
import threading

import paho.mqtt.client as mqtt

from app.core.config import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_client: mqtt.Client | None = None
_owner_pid: int | None = None


def _build_client() -> mqtt.Client | None:
    """Create and connect a paho client. Returns ``None`` on failure."""

    # paho-mqtt 2.x requires ``callback_api_version`` while 1.x does not
    # accept it. Build the client kwargs accordingly so the same source works
    # under both versions.
    client_kwargs: dict = {"client_id": f"{settings.MQTT_CLIENT_ID}-{os.getpid()}"}
    callback_api_version = getattr(mqtt, "CallbackAPIVersion", None)
    if callback_api_version is not None:
        client_kwargs["callback_api_version"] = callback_api_version.VERSION2

    try:
        client = mqtt.Client(**client_kwargs)
    except TypeError:
        # Fallback for very old paho versions.
        client = mqtt.Client(client_id=client_kwargs["client_id"])

    if settings.MQTT_USERNAME:
        client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

    try:
        client.connect(settings.MQTT_HOST, settings.MQTT_PORT, keepalive=60)
        client.loop_start()
        return client
    except Exception as exc:  # noqa: BLE001 - network errors must not abort startup
        logger.warning("MQTT connect to %s:%s failed: %s", settings.MQTT_HOST, settings.MQTT_PORT, exc)
        try:
            client.loop_stop()
        except Exception:  # noqa: BLE001
            pass
        return None


def _get_client() -> mqtt.Client | None:
    """Return a process-local connected client, reconnecting if needed."""

    global _client, _owner_pid
    pid = os.getpid()
    with _lock:
        if _client is None or _owner_pid != pid:
            # Either first use or we've been forked into a new process.
            _client = _build_client()
            _owner_pid = pid
        return _client


def _drop_client() -> None:
    global _client, _owner_pid
    with _lock:
        if _client is not None:
            try:
                _client.loop_stop()
                _client.disconnect()
            except Exception:  # noqa: BLE001
                pass
        _client = None
        _owner_pid = None


def publish(topic: str, payload: dict) -> bool:
    """Publish a JSON payload to ``topic``.

    Returns ``True`` if the broker accepted the publish, ``False`` if it had
    to fall back to the mock log path. The boolean is purely informational;
    callers should not rely on it for delivery guarantees - that is what the
    outbox + retry loop is for.
    """

    body = json.dumps(payload, ensure_ascii=False)
    client = _get_client()
    if client is not None:
        try:
            info = client.publish(topic, body, qos=1)
            # ``rc`` 0 means MQTT_ERR_SUCCESS; non-zero indicates a queueing
            # error (e.g., disconnected). Force a reconnect on next call.
            if getattr(info, "rc", 0) == 0:
                return True
            logger.warning("MQTT publish returned rc=%s for topic %s", info.rc, topic)
        except Exception as exc:  # noqa: BLE001
            logger.warning("MQTT publish failed for topic %s: %s", topic, exc)
        _drop_client()

    logger.info("[MOCK MQTT] %s %s", topic, body)
    return False
