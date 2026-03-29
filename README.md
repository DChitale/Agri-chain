# Agri-Chain

An AIoT, Machine Learning, and Blockchain-powered ecosystem for verifiable Soil Organic Carbon (SOC) tracking and Carbon Credit issuance.

## Overview
Agri-Chain connects local agriculture sensor data to a global immutable ledger. The project monitors soil metrics in real-time, predicts Soil Organic Carbon (SOC) levels using a machine learning model, and verifies these readings on-chain via a cryptographic oracle to issue trustless carbon credits.

### Core Architecture:
1. **IoT Node**: ESP32 collects temperature, humidity, and soil moisture data and pushes it over MQTT.
2. **Data Pipeline**: Mosquitto brokers the IoT data, which is parsed by Python subscribers and stored in InfluxDB. Grafana Visualizes the data.
3. **AI/ML Engine**: A Random Forest model aggregates the daily data to train and predict Soil Organic Carbon (SOC) percentages.
4. **Web3 Oracle**: A Python-based oracle gathers SOC predictions, hashes them (SHA-256), signs the data, and securely transmits attestations to a Smart Contract.
5. **Decentralized Ledger**: A Solidity Smart contract mints/verifies carbon credits.

---

## Folder Structure

```text
Agri-chain/
├── code/                     # C++/Arduino code for IoT hardware
│   ├── code.ino              # Main ESP32 sketch
│   └── secrets.h             # WiFi & Server Credentials (Ignored in Git)
├── contract/                 # Solidity smart contracts
│   ├── CarbonCredit.sol      # Main Carbon Credit tracking logic
│   └── abi.json              # Contract Application Binary Interface (ABI)
├── data/                     # Local data mapping
│   ├── raw/                  # Placeholder for CSV dumps / raw datasets
│   ├── mosquitto/            # Docker persistent volume for MQTT
│   ├── influxdb/             # Docker persistent volume for DB
│   └── grafana/              # Docker persistent volume for Dashboards
├── model/                    # Machine Learning workflow
│   ├── train.py              # Script to train the Random Forest
│   └── soc_model.pkl         # Serialized (exported) ML model
├── oracle/                   # Blockchain interfacing components
│   ├── signer.py             # SHA-256 hashing and web3.py cryptographic signing
│   └── transmit.py           # Submits the signed attestation to the blockchain
├── pipeline/                 # Data orchestration
│   ├── mqtt_subscriber.py    # Subscribes to MQTT & writes to InfluxDB
│   ├── aggregator.py         # Daily Pandas aggregation script
│   └── validator.py          # Data sanity checks prior to ML processing
├── .env                      # Universal configuration file (Keys, URLs)
├── docker-compose.yml        # Docker config for MQTT, InfluxDB, Grafana
└── oracle_script.py          # Main oracle execution/testing entry point
```

---

## Setup Instructions

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.9+
- Arduino IDE (with ESP32 board support and PubSubClient, DHT libraries installed)
- Node/npm (Optional: for local contract compilation if you don't use Remix)

### 2. Infrastructure (Databases & Brokers)
Start the foundational services (Mosquitto MQTT, InfluxDB, and Grafana) using Docker:
```bash
docker-compose up -d
```
- **MQTT Broker**: `localhost:1883`
- **InfluxDB**: `http://localhost:8086`
- **Grafana**: `http://localhost:3000`

### 3. Environment Variables
Ensure you populate your `.env` file at the root of the project.
```ini
# Sepolia Testnet Configuration
SEPOLIA_RPC_URL=your_sepolia_rpc_url_here
PRIVATE_KEY=your_private_key_here

# Database Configuration
INFLUXDB_DB=agrichain
INFLUXDB_ADMIN_USER=admin
INFLUXDB_ADMIN_PASSWORD=password

# MQTT Configuration
MQTT_BROKER=192.168.x.x
MQTT_PORT=1883

# WiFi Configuration (Private)
WIFI_SSID=YourWiFi
WIFI_PASS=YourPassword
```

### 4. IoT Sensor Node Setup (ESP32)
1. Open `code/code.ino` in your Arduino IDE.
2. In the `code/` folder, ensure `secrets.h` specifies the IP address to point to the host machine running your Docker containers:
   ```c
   #define WIFI_SSID "YourWiFi"
   #define WIFI_PASS "YourPassword"
   #define IP_ADDRESS "192.168.x.x" // Must match your host machine IP
   ```
3. Flash the code to your ESP32. You can monitor the generic output via the Serial Monitor (115200 baud).

### 5. Python Environment Setup
Install the required python dependencies:
```bash
pip install paho-mqtt influxdb-client pandas scikit-learn web3 python-dotenv
```

---

## Running the Project

### Phase 1: Data Collection & Subscribing
Start the MQTT to InfluxDB ingestion service:
```bash
python pipeline/mqtt_subscriber.py
```
*At this point, you should see data flowing from your ESP32 through Mosquitto directly into InfluxDB.*

### Phase 2: Processing & Machine Learning
Once sufficient data is gathered, aggregate data and train the model:
```bash
python pipeline/aggregator.py
python pipeline/validator.py
python model/train.py
```
*This will output an updated `soc_model.pkl`.*

### Phase 3: Smart Contract & Blockchain Oracle
1. Deploy `contract/CarbonCredit.sol` to the Sepolia testnet using Remix, Truffle, or Foundry.
2. Extract the ABI and paste it into `contract/abi.json`.
3. Put the deployed Contract Address in your Oracle scripts.
4. Run the oracle to sign daily data and execute the on-chain attestation:
```bash
python oracle/transmit.py
```

## Security Notes
- Protect your `.env` and `code/secrets.h` securely. They contain private keys and passwords and are specifically added to `.gitignore`. Never upload them to a public repository!
