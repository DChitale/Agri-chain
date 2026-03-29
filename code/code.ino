#include <WiFi.h>
#include "secrets.h"
#include <PubSubClient.h>
#include <DHT.h>

// --- Configuration ---
const char* ssid = WIFI_SSID;
const char* password = WIFI_PASS;
const char* mqtt_server = IP_ADDRESS; // Your Raspberry Pi IP

#define DHTPIN 14
#define DHTTYPE DHT22
#define SOIL_PIN 34

// --- Objects ---
WiFiClient espClient;
PubSubClient client(espClient);
DHT dht(DHTPIN, DHTTYPE);

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    String clientId = "ESP32Node-";
    clientId += String(random(0xffff), HEX);

    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" retrying in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  dht.begin();
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  float h = dht.readHumidity();
  float t = dht.readTemperature();
  int soilValue = analogRead(SOIL_PIN);

  int soilPercent = map(soilValue, 4095, 1500, 0, 100);
  soilPercent = constrain(soilPercent, 0, 100);

  if (isnan(h) || isnan(t)) {
    Serial.println("Failed to read from DHT!");
    return;
  }

  String payload = "{";
  payload += "\"node_id\":\"node_01\",";
  payload += "\"temp\":" + String(t) + ",";
  payload += "\"humidity\":" + String(h) + ",";
  payload += "\"soil_moisture\":" + String(soilPercent);
  payload += "}";

  Serial.println(payload);
  client.publish("farm/sensors", payload.c_str());

  delay(10000);
}