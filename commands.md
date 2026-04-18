# Agri-chain Command Cheatsheet

---

## Setup

```bash
# Activate venv (always do this first)
cd ~/Agri-chain
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Services

```bash
# Start InfluxDB
sudo systemctl start influxdb
sudo systemctl status influxdb

# Start MQTT subscriber (auto-writes to InfluxDB)
sudo systemctl start agrichain-subscriber
sudo systemctl status agrichain-subscriber

# Restart subscriber after code changes
sudo systemctl restart agrichain-subscriber

# View subscriber live logs
sudo journalctl -u agrichain-subscriber -f
```

---

## Data Verification

```bash
# Check live MQTT messages from ESP32
mosquitto_sub -h localhost -t "farm/sensors" -v

# Check how many readings in last 24h
python3 pipeline/test_aggregator.py

# View daily aggregates CSV
cat data/daily_aggregates.csv

# Insert 20 test readings (when ESP32 not connected)
python3 -c "
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import os
load_dotenv()
client = InfluxDBClient(url=os.getenv('INFLUX_URL'), token=os.getenv('INFLUX_TOKEN'), org=os.getenv('INFLUX_ORG'))
write_api = client.write_api(write_options=SYNCHRONOUS)
now = datetime.now(timezone.utc)
for i in range(20):
    point = (Point('sensor_reading').tag('node_id','node_01')
        .field('temperature', 28.5).field('humidity', 60.0).field('soil_moisture', 40.0)
        .time(now - timedelta(minutes=i*10), WritePrecision.NS))
    write_api.write(bucket=os.getenv('INFLUX_BUCKET'), record=point)
client.close()
print('[+] Done')
"
```

---

## ML Pipeline

```bash
# Run anomaly detection on last 24h
KERAS_BACKEND=torch python3 pipeline/anomaly_detector.py

# Run daily aggregation + SOC prediction
python3 pipeline/aggregator.py

# Run validator test
python3 pipeline/validator.py
```

---

## Blockchain

```bash
# Run full pipeline manually (aggregate + validate + mint)
KERAS_BACKEND=torch python3 main.py

# Read token data from blockchain (change token ID as needed)
python3 -c "
import json
from web3 import Web3
from dotenv import load_dotenv
import os
load_dotenv()
w3 = Web3(Web3.HTTPProvider(os.getenv('SEPOLIA_RPC_URL')))
contract = w3.eth.contract(address=os.getenv('CONTRACT_ADDRESS'), abi=json.load(open('contract/abi.json')))
print(contract.functions.credits(0).call())
"
```

---

## Certificate

```bash
# Generate PDF certificate for token ID 0
python3 certificate/generate.py 0

# Generate for token ID 1
python3 certificate/generate.py 1

# Serve files to download on laptop
python3 -m http.server 8000
# Then open http://192.168.1.41:8000/certificates/
```

---

## Cron Job

```bash
# Edit cron schedule
crontab -e

# Current schedule (runs daily at 11 PM)
# 0 23 * * * /home/dc/Agri-chain/venv/bin/python3 /home/dc/Agri-chain/main.py

# View cron logs
journalctl -u cron -f
```

---

## Etherscan

```
Contract:  https://sepolia.etherscan.io/address/0x9E8d45f4BE5768631F31c5b797Ca23809032E882
Farmer:    https://sepolia.etherscan.io/address/0x0982794EeE47c7fb8eFAeD8A960242CBe7f99bEA
Device:    https://sepolia.etherscan.io/address/0x8c47Fb2bBd5B4ee0cf8832945D6431692e86C448
```

---

## InfluxDB UI

```
http://192.168.1.41:8086
Org:    agrichain
Bucket: farm_sensors
```