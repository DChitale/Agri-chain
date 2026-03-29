# MQTT → InfluxDB writer
# This script subscribes to MQTT topics and writes received data to InfluxDB.
import json
import os
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timezone

# Load variables from .env file
load_dotenv()

# InfluxDB config
INFLUX_URL    = os.getenv("INFLUX_URL")
INFLUX_TOKEN  = os.getenv("INFLUX_TOKEN")
INFLUX_ORG    = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

# MQTT config
MQTT_BROKER   = os.getenv("MQTT_BROKER")
MQTT_PORT     = int(os.getenv("MQTT_PORT"))
MQTT_TOPIC    = os.getenv("MQTT_TOPIC")

write_api = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG).write_api(write_options=SYNCHRONOUS)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        point = (
            Point("sensor_reading")
            .tag("node_id", data["node_id"])
            .field("temperature",    data["temp"])
            .field("humidity",       data["humidity"])
            .field("soil_moisture",  data["soil_moisture"])
            .time(datetime.now(timezone.utc), WritePrecision.NANOSECONDS)
        )
        write_api.write(bucket=INFLUX_BUCKET, record=point)
        print(f"[+] Written: {data}")
    except Exception as e:
        print(f"[!] Error: {e}")

client = mqtt.Client()
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT)
client.subscribe(MQTT_TOPIC)
print(f"Listening on {MQTT_TOPIC}...")
client.loop_forever()