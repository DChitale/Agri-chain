# Train Random Forest
# This script trains a Random Forest model for Soil Organic Carbon (SOC) prediction.
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import pickle

df = pd.read_csv("synthetic_soc_training.csv")

X = df[["avg_temperature", "avg_humidity", "avg_soil_moisture", "env_stress"]]
y = df["soc_percent"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

preds = model.predict(X_test)
print(f"MAE: {mean_absolute_error(y_test, preds):.4f}")
print(f"R2:  {r2_score(y_test, preds):.4f}")

with open("soc_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("[+] Model saved as soc_model.pkl")