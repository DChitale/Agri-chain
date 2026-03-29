import os
import pickle
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

MODEL_PATH = "model/soc_model.pkl"
SOC_MIN    = 0.3   # minimum realistic SOC% for Indian farmland
SOC_MAX    = 2.5   # maximum realistic SOC%
MAX_DAILY_CHANGE = 0.5  # SOC can't change more than 0.5% in one day

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

def validate_soc(soc, previous_soc=None):
    if not (SOC_MIN <= soc <= SOC_MAX):
        return False, f"SOC {soc}% out of range ({SOC_MIN}-{SOC_MAX}%)"

    if previous_soc is not None:
        change = abs(soc - previous_soc)
        if change > MAX_DAILY_CHANGE:
            return False, f"SOC changed too fast: {change:.2f}% in one day"

    return True, "OK"

def get_previous_soc(csv_path="data/daily_aggregates.csv"):
    if not os.path.exists(csv_path):
        return None
    df = pd.read_csv(csv_path)
    if "soc_percent" not in df.columns or df.empty:
        return None
    return float(df["soc_percent"].iloc[-1])

if __name__ == "__main__":
    # Test with sample data
    soc = predict_soc(
        avg_temperature=31.68,
        avg_humidity=45.49,
        avg_soil_moisture=0.0,
        env_stress=1
    )
    print(f"[+] Predicted SOC: {soc}%")

    previous = get_previous_soc()
    valid, reason = validate_soc(soc, previous)
    print(f"[+] Valid: {valid} — {reason}")