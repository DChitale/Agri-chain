import numpy as np
import pandas as pd
import os

np.random.seed(42)
NUM_SAMPLES = 2000

# Realistic Indian farmland ranges
temperature    = np.random.uniform(20, 42, NUM_SAMPLES)   # °C
humidity       = np.random.uniform(20, 90, NUM_SAMPLES)   # %
soil_moisture  = np.random.uniform(5,  80, NUM_SAMPLES)   # %
env_stress     = np.random.randint(0,  4,  NUM_SAMPLES)   # 0-3

# SOC logic based on agronomy:
# - Higher moisture → higher SOC
# - Lower temp → higher SOC (less decomposition)
# - Higher humidity → higher SOC
# - Higher stress → lower SOC
soc = (
    0.3
    + (soil_moisture / 80)  * 1.2
    + (humidity / 90)       * 0.5
    - (temperature / 42)    * 0.4
    - (env_stress / 3)      * 0.3
    + np.random.normal(0, 0.1, NUM_SAMPLES)  # noise
)

# Clamp to realistic Indian SOC range: 0.3% - 2.5%
soc = np.clip(soc, 0.3, 2.5)

df = pd.DataFrame({
    "avg_temperature":   np.round(temperature, 2),
    "avg_humidity":      np.round(humidity, 2),
    "avg_soil_moisture": np.round(soil_moisture, 2),
    "env_stress":        env_stress,
    "soc_percent":       np.round(soc, 3)
})

os.makedirs("data", exist_ok=True)
df.to_csv("data/synthetic_soc_training.csv", index=False)
print(f"[+] Generated {NUM_SAMPLES} samples")
print(df.describe())