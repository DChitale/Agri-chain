import os
import pickle
import numpy as np
import pandas as pd
import keras
from dotenv import load_dotenv

load_dotenv()

MODEL_PATH     = "model/anomaly_model.keras"
SCALER_PATH    = "model/anomaly_scaler.pkl"
THRESHOLD_PATH = "model/anomaly_threshold.txt"
SEQ_LEN        = 12
FEATURES       = ["temperature", "humidity", "soil_moisture"]

# Load model, scaler, threshold
model = keras.models.load_model(MODEL_PATH)

with open(SCALER_PATH, "rb") as f:
    scaler = pickle.load(f)

with open(THRESHOLD_PATH, "r") as f:
    THRESHOLD = float(f.read().strip())

print(f"[+] Anomaly threshold: {THRESHOLD:.6f}")

def detect(df: pd.DataFrame) -> pd.DataFrame:
    data = scaler.transform(df[FEATURES])

    if len(data) < SEQ_LEN:
        print(f"[!] Need at least {SEQ_LEN} readings, got {len(data)}")
        return df

    # Build sequences
    sequences = []
    for i in range(len(data) - SEQ_LEN):
        sequences.append(data[i:i+SEQ_LEN])
    sequences = np.array(sequences)

    # Reconstruct and calculate error
    preds  = model.predict(sequences, verbose=0)
    errors = np.mean(np.abs(sequences - preds), axis=(1, 2))

    # Pad first SEQ_LEN rows with NaN (no sequence available)
    anomaly_scores = np.concatenate([np.full(SEQ_LEN, np.nan), errors])
    anomaly_flags  = np.concatenate([np.zeros(SEQ_LEN), (errors > THRESHOLD).astype(int)])

    df = df.copy()
    df["reconstruction_error"] = anomaly_scores
    df["is_anomaly"]           = anomaly_flags
    return df

def run_on_influx():
    from influxdb_client import InfluxDBClient
    import os

    client    = InfluxDBClient(url=os.getenv("INFLUX_URL"), token=os.getenv("INFLUX_TOKEN"), org=os.getenv("INFLUX_ORG"))
    query_api = client.query_api()

    query = f'''
    from(bucket: "{os.getenv("INFLUX_BUCKET")}")
      |> range(start: -24h)
      |> filter(fn: (r) => r._measurement == "sensor_reading")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    df = query_api.query_data_frame(query)
    client.close()

    if df.empty:
        print("[!] No data found")
        return

    df = df.rename(columns={"_time": "timestamp"})
    result = detect(df)

    anomalies = result[result["is_anomaly"] == 1]
    print(f"[+] Total readings: {len(result)}")
    print(f"[!] Anomalies detected: {len(anomalies)}")

    if not anomalies.empty:
        print(anomalies[["timestamp", "temperature", "humidity", "soil_moisture", "reconstruction_error"]])

if __name__ == "__main__":
    run_on_influx()