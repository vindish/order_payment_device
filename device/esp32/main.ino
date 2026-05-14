// Order Payment Device - ESP32 reference firmware.
//
// Responsibilities:
//   * Connect to Wi-Fi and keep the connection alive.
//   * Connect to the project's MQTT broker and subscribe to
//     "device/<DEVICE_SN>/cmd". When an "unlock" command arrives the
//     firmware drives the lock GPIO, then reports back via HTTP.
//   * Acknowledge each command through POST /api/v1/devices/commands/ack
//     and report unlock completion through
//     POST /api/v1/devices/events/unlocked?order_id=<id>.
//   * Send periodic heartbeats so the backend marks the device ONLINE.
//
// Required Arduino libraries:
//   * WiFi (ESP32 core)
//   * PubSubClient by Nick O'Leary
//   * ArduinoJson by Benoit Blanchon
//   * HTTPClient (ESP32 core)
//
// Replace the credentials in the CONFIG section before flashing.

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ---------------------------------------------------------------------------
// CONFIG - replace with values that match your deployment
// ---------------------------------------------------------------------------
static const char* WIFI_SSID      = "your-ssid";
static const char* WIFI_PASSWORD  = "your-wifi-password";

static const char* MQTT_HOST      = "192.168.1.100";  // Mosquitto host
static const uint16_t MQTT_PORT   = 1883;
static const char* MQTT_USERNAME  = "";                // empty disables auth
static const char* MQTT_PASSWORD  = "";

static const char* DEVICE_SN      = "LOCK-001";
static const char* DEVICE_TOKEN   = "replace-with-device-secret";  // value
                                  // returned by POST /api/v1/devices

static const char* API_BASE       = "http://192.168.1.100:8000/api/v1";

static const uint8_t LOCK_GPIO        = 5;     // active-high relay
static const uint32_t LOCK_PULSE_MS   = 500;   // unlock pulse width
static const uint32_t HEARTBEAT_MS    = 30000; // heartbeat interval


// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
static WiFiClient   wifiClient;
static PubSubClient mqttClient(wifiClient);
static String       cmdTopic;
static uint32_t     lastHeartbeatMs = 0;

// ---------------------------------------------------------------------------
// Wi-Fi
// ---------------------------------------------------------------------------
static void ensureWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }
  Serial.printf("[WiFi] connecting to %s\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
    delay(250);
    Serial.print('.');
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WiFi] connected, ip=%s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\n[WiFi] connect timeout, will retry");
  }
}

// ---------------------------------------------------------------------------
// HTTP helpers (POST JSON with X-Device-SN / X-Device-Token headers)
// ---------------------------------------------------------------------------
static int postJson(const String& path, const String& body) {
  if (WiFi.status() != WL_CONNECTED) {
    return -1;
  }
  HTTPClient http;
  String url = String(API_BASE) + path;
  if (!http.begin(url)) {
    Serial.printf("[HTTP] begin failed: %s\n", url.c_str());
    return -1;
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-SN", DEVICE_SN);
  http.addHeader("X-Device-Token", DEVICE_TOKEN);
  int status = http.POST(body);
  if (status > 0) {
    Serial.printf("[HTTP] POST %s -> %d\n", path.c_str(), status);
  } else {
    Serial.printf("[HTTP] POST %s failed: %s\n", path.c_str(), http.errorToString(status).c_str());
  }
  http.end();
  return status;
}

static void sendHeartbeat() {
  String path = "/devices/" + String(DEVICE_SN) + "/heartbeat";
  postJson(path, "{}");
}

static void ackCommand(long commandId, const char* status, const char* errorMessage) {
  StaticJsonDocument<256> doc;
  doc["command_id"] = commandId;
  doc["status"] = status;
  if (errorMessage != nullptr) {
    doc["error_message"] = errorMessage;
  }
  String body;
  serializeJson(doc, body);
  postJson("/devices/commands/ack", body);
}

static void reportUnlocked(long orderId) {
  String path = "/devices/events/unlocked?order_id=" + String(orderId);
  postJson(path, "{}");
}


// ---------------------------------------------------------------------------
// Lock control
// ---------------------------------------------------------------------------
static void pulseLock() {
  digitalWrite(LOCK_GPIO, HIGH);
  delay(LOCK_PULSE_MS);
  digitalWrite(LOCK_GPIO, LOW);
}

// ---------------------------------------------------------------------------
// MQTT command handler
// ---------------------------------------------------------------------------
static void handleUnlock(long commandId, JsonObjectConst payload) {
  long orderId = payload["order_id"] | 0L;
  Serial.printf("[CMD] unlock order_id=%ld command_id=%ld\n", orderId, commandId);

  // Tell the backend we received the command.
  ackCommand(commandId, "ACKED", nullptr);

  // Drive the lock and report the outcome.
  pulseLock();

  if (orderId > 0) {
    reportUnlocked(orderId);
  }
  ackCommand(commandId, "DONE", nullptr);
}

static void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  Serial.printf("[MQTT] %s (%u bytes)\n", topic, length);

  StaticJsonDocument<512> doc;
  DeserializationError err = deserializeJson(doc, payload, length);
  if (err) {
    Serial.printf("[MQTT] json parse failed: %s\n", err.c_str());
    return;
  }

  long commandId = doc["command_id"] | 0L;
  const char* cmd = doc["cmd"] | "";
  JsonObjectConst body = doc["payload"].as<JsonObjectConst>();

  if (strcmp(cmd, "unlock") == 0) {
    handleUnlock(commandId, body);
  } else {
    Serial.printf("[CMD] unsupported command: %s\n", cmd);
    ackCommand(commandId, "FAILED", "unsupported command");
  }
}

// ---------------------------------------------------------------------------
// MQTT lifecycle
// ---------------------------------------------------------------------------
static void ensureMqtt() {
  if (mqttClient.connected()) {
    return;
  }
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  mqttClient.setCallback(onMqttMessage);
  mqttClient.setKeepAlive(30);
  mqttClient.setBufferSize(1024);

  String clientId = String("esp32-") + DEVICE_SN;
  bool ok;
  if (strlen(MQTT_USERNAME) > 0) {
    ok = mqttClient.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD);
  } else {
    ok = mqttClient.connect(clientId.c_str());
  }

  if (ok) {
    Serial.printf("[MQTT] connected as %s\n", clientId.c_str());
    mqttClient.subscribe(cmdTopic.c_str(), 1);
    Serial.printf("[MQTT] subscribed %s\n", cmdTopic.c_str());
  } else {
    Serial.printf("[MQTT] connect failed rc=%d, retry later\n", mqttClient.state());
    delay(1000);
  }
}


// ---------------------------------------------------------------------------
// Arduino entry points
// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(LOCK_GPIO, OUTPUT);
  digitalWrite(LOCK_GPIO, LOW);

  cmdTopic = String("device/") + DEVICE_SN + "/cmd";

  ensureWifi();
  ensureMqtt();
  sendHeartbeat();
  lastHeartbeatMs = millis();
}

void loop() {
  ensureWifi();
  ensureMqtt();
  mqttClient.loop();

  uint32_t now = millis();
  if (now - lastHeartbeatMs >= HEARTBEAT_MS) {
    sendHeartbeat();
    lastHeartbeatMs = now;
  }

  delay(10);
}
