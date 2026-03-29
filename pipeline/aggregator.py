import os
import pickle
import pandas as pd
from influxdb_client import InfluxDBClient
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

INFLUX_URL    = os.getenv("INFLUX_URL")
INFLUX_TOKEN  = os.getenv("INFLUX_TOKEN")
INFLUX_ORG    = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

OUTPUT_CSV = "data/daily_aggregates.csv"
MODEL_PATH = "model/soc_model.pkl"

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

def predict_soc(avg_temperature, avg_humidity, avg_soil_moisture, env_stress):
    X = pd.DataFrame([{
        "avg_temperature":   avg_temperature,
        "avg_humidity":      avg_humidity,
        "avg_soil_moisture": avg_soil_moisture,
        "env_stress":        env_stress
    }])
    return round(float(model.predict(X)[0]), 4)

def fetch_last_24h():
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = client.query_api()

    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -24h)
      |> filter(fn: (r) => r._measurement == "sensor_reading")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''

    tables = query_api.query_data_frame(query)
    client.close()
    return tables

def calculate_stress(row):
    stress = 0
    if row["temperature"] > 35:
        stress += 1
    if row["humidity"] < 30:
        stress += 1
    if row["soil_moisture"] < 20:
        stress += 1
    return stress

def aggregate():
    df = fetch_last_24h()

    if df.empty:
        print("[!] No data found in last 24h")
        return

    daily = {
        "date":             datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "avg_temperature":  round(df["temperature"].mean(), 2),
        "avg_humidity":     round(df["humidity"].mean(), 2),
        "avg_soil_moisture":round(df["soil_moisture"].mean(), 2),
        "max_temperature":  round(df["temperature"].max(), 2),
        "min_soil_moisture":round(df["soil_moisture"].min(), 2),
    }

    daily["env_stress"] = calculate_stress({
        "temperature":  daily["avg_temperature"],
        "humidity":     daily["avg_humidity"],
        "soil_moisture":daily["avg_soil_moisture"],
    })

    daily["soc_percent"] = predict_soc(
        daily["avg_temperature"],
        daily["avg_humidity"],
        daily["avg_soil_moisture"],
        daily["env_stress"]
    )

    row_df = pd.DataFrame([daily])

    os.makedirs("data", exist_ok=True)
    if os.path.exists(OUTPUT_CSV):
        row_df.to_csv(OUTPUT_CSV, mode="a", header=False, index=False)
    else:
        row_df.to_csv(OUTPUT_CSV, index=False)

    print(f"[+] Aggregated: {daily}")

if __name__ == "__main__":
    aggregate()