import json
import logging

import paho.mqtt.client as mqtt

from app.core.config import settings

logger = logging.getLogger(__name__)
client = mqtt.Client(client_id=settings.MQTT_CLIENT_ID)

if settings.MQTT_USERNAME:
    client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

try:
    client.connect(settings.MQTT_HOST, settings.MQTT_PORT, 60)
    client.loop_start()
except Exception as exc:
    logger.warning("MQTT is unavailable, using degraded publish mode: %s", exc)
    client = None


def publish(topic: str, payload: dict):
    body = json.dumps(payload, ensure_ascii=False)
    if client:
        client.publish(topic, body, qos=1)
        return
    logger.info("[MOCK MQTT] %s %s", topic, body)
