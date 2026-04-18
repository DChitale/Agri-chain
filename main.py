import os
import json
import hashlib
import pickle
import numpy as np
import pandas as pd
os.environ["KERAS_BACKEND"] = "torch"
import keras
from web3 import Web3
from eth_account.messages import encode_defunct
from influxdb_client import InfluxDBClient
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# --- Config ---
INFLUX_URL       = os.getenv("INFLUX_URL")
INFLUX_TOKEN     = os.getenv("INFLUX_TOKEN")
INFLUX_ORG       = os.getenv("INFLUX_ORG")
INFLUX_BUCKET    = os.getenv("INFLUX_BUCKET")
SEPOLIA_RPC_URL  = os.getenv("SEPOLIA_RPC_URL")
DEVICE_ADDRESS   = os.getenv("DEVICE_ADDRESS")
DEVICE_PRIVATE_KEY = os.getenv("DEVICE_PRIVATE_KEY")
FARMER_ADDRESS   = os.getenv("FARMER_ADDRESS")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

OUTPUT_CSV      = "data/daily_aggregates.csv"
MODEL_PATH      = "model/soc_model.pkl"
ANOMALY_MODEL   = "model/anomaly_model.keras"
ANOMALY_SCALER  = "model/anomaly_scaler.pkl"
ANOMALY_THRESH  = "model/anomaly_threshold.txt"
SEQ_LEN         = 12
FEATURES        = ["temperature", "humidity", "soil_moisture"]
SOC_MIN    = 0.3
SOC_MAX    = 2.5
MAX_DAILY_CHANGE = 0.5

# --- Load models and contract ---
with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

anomaly_model = keras.models.load_model(ANOMALY_MODEL)
with open(ANOMALY_SCALER, "rb") as f:
    anomaly_scaler = pickle.load(f)
with open(ANOMALY_THRESH) as f:
    ANOMALY_THRESHOLD = float(f.read().strip())

with open("contract/abi.json") as f:
    ABI = json.load(f)

w3       = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))
contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=ABI)

# --- Step 1: Fetch from InfluxDB ---
def fetch_last_24h():
    client    = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = client.query_api()
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -24h)
      |> filter(fn: (r) => r._measurement == "sensor_reading")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    df = query_api.query_data_frame(query)
    client.close()
    return df

# --- Step 1b: Anomaly Detection ---
def check_anomalies(df):
    data = anomaly_scaler.transform(df[FEATURES])
    if len(data) < SEQ_LEN:
        print(f"[!] Not enough data for anomaly detection (need {SEQ_LEN})")
        return 0
    sequences = np.array([data[i:i+SEQ_LEN] for i in range(len(data) - SEQ_LEN)])
    preds  = anomaly_model.predict(sequences, verbose=0)
    errors = np.mean(np.abs(sequences - preds), axis=(1, 2))
    n_anomalies = int(np.sum(errors > ANOMALY_THRESHOLD))
    return n_anomalies

# --- Step 2: Aggregate ---
def aggregate(df):
    daily = {
        "date":              datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "avg_temperature":   round(float(df["temperature"].mean()), 2),
        "avg_humidity":      round(float(df["humidity"].mean()), 2),
        "avg_soil_moisture": round(float(df["soil_moisture"].mean()), 2),
        "max_temperature":   round(float(df["temperature"].max()), 2),
        "min_soil_moisture": round(float(df["soil_moisture"].min()), 2),
    }
    stress = 0
    if daily["avg_temperature"] > 35:  stress += 1
    if daily["avg_humidity"] < 30:     stress += 1
    if daily["avg_soil_moisture"] < 20: stress += 1
    daily["env_stress"] = stress
    return daily

# --- Step 3: Predict SOC ---
def predict_soc(daily):
    X = pd.DataFrame([{
        "avg_temperature":   daily["avg_temperature"],
        "avg_humidity":      daily["avg_humidity"],
        "avg_soil_moisture": daily["avg_soil_moisture"],
        "env_stress":        daily["env_stress"]
    }])
    return round(float(model.predict(X)[0]), 4)

# --- Step 4: Validate SOC ---
def validate_soc(soc):
    if not (SOC_MIN <= soc <= SOC_MAX):
        return False, f"SOC {soc}% out of range"
    if os.path.exists(OUTPUT_CSV):
        df = pd.read_csv(OUTPUT_CSV)
        if "soc_percent" in df.columns and not df.empty:
            prev = float(df["soc_percent"].iloc[-1])
            if abs(soc - prev) > MAX_DAILY_CHANGE:
                return False, f"SOC changed too fast: {abs(soc-prev):.2f}%"
    return True, "OK"

# --- Step 5: Hash + Sign + Mint ---
def mint(daily, soc):
    sensor_data = {
        "node_id":          "node_01",
        "date":             daily["date"],
        "avg_temperature":  daily["avg_temperature"],
        "avg_humidity":     daily["avg_humidity"],
        "avg_soil_moisture":daily["avg_soil_moisture"],
        "env_stress":       daily["env_stress"],
    }

    data_hash  = hashlib.sha256(json.dumps(sensor_data, sort_keys=True).encode()).digest()
    signed     = w3.eth.account.sign_message(encode_defunct(data_hash), private_key=DEVICE_PRIVATE_KEY)
    soc_scaled = int(soc * 1000)
    nonce      = w3.eth.get_transaction_count(Web3.to_checksum_address(DEVICE_ADDRESS))

    txn = contract.functions.mint(
        Web3.to_checksum_address(FARMER_ADDRESS),
        Web3.to_checksum_address(DEVICE_ADDRESS),
        "node_01",
        soc_scaled,
        data_hash,
        signed.signature
    ).build_transaction({
        "from":     Web3.to_checksum_address(DEVICE_ADDRESS),
        "nonce":    nonce,
        "gas":      300000,
        "gasPrice": w3.eth.gas_price,
    })

    signed_txn = w3.eth.account.sign_transaction(txn, private_key=DEVICE_PRIVATE_KEY)
    tx_hash    = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    receipt    = w3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash.hex(), receipt.blockNumber

# --- Main ---
def main():
    print(f"\n[Agri-chain] {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    df = fetch_last_24h()
    if df.empty:
        print("[!] No sensor data in last 24h. Exiting.")
        return

    n_anomalies = check_anomalies(df)
    if n_anomalies > 0:
        print(f"[!] {n_anomalies} anomalies detected in sensor data. Aborting mint.")
        return
    print(f"[+] No anomalies detected")

    daily = aggregate(df)
    soc   = predict_soc(daily)
    daily["soc_percent"] = soc
    print(f"[+] SOC predicted: {soc}%")

    valid, reason = validate_soc(soc)
    if not valid:
        print(f"[!] Validation failed: {reason}")
        return
    print(f"[+] Validation passed")

    # Save to CSV
    os.makedirs("data", exist_ok=True)
    row_df = pd.DataFrame([daily])
    if os.path.exists(OUTPUT_CSV):
        row_df.to_csv(OUTPUT_CSV, mode="a", header=False, index=False)
    else:
        row_df.to_csv(OUTPUT_CSV, index=False)

    tx_hash, block = mint(daily, soc)
    print(f"[+] NFT minted | TX: {tx_hash} | Block: {block}")
    print(f"[+] Etherscan: https://sepolia.etherscan.io/tx/0x{tx_hash}")

if __name__ == "__main__":
    main()