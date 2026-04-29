import paho.mqtt.client as mqtt
import json

client = mqtt.Client()

try:
    client.connect("localhost", 1883, 60)
except Exception as e:
    print("⚠️ MQTT 未启动，进入降级模式", e)
    client = None


def publish(topic: str, payload: dict):
    if client:
        client.publish(topic, json.dumps(payload), qos=1)
    else:
        print(f"[MOCK MQTT] {topic} {payload}")