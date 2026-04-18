# Agri-chain

A decentralized carbon credit system for farmers using IoT sensors, edge AI, and blockchain.

Soil Organic Carbon (SOC) is measured via ESP32 sensors, predicted using a Random Forest model on a Raspberry Pi, and minted as an NFT carbon credit on the Ethereum Sepolia testnet.

---

## Architecture

```
ESP32 Sensors → MQTT → Raspberry Pi → InfluxDB
                                         ↓
                                   Aggregation (Pandas)
                                         ↓
                                   SOC Prediction (Random Forest)
                                         ↓
                                   Validation
                                         ↓
                              SHA-256 Hash + Pi Signing (web3.py)
                                         ↓
                              Smart Contract (Sepolia) → NFT to Farmer Wallet
```

---

## Hardware

- ESP32 + DHT22 (temperature/humidity) +  soil moisture sensor
- Raspberry Pi 4B (8GB) — edge AI + Web3 oracle

---

## Project Structure

```
Agri-chain/
├── main.py                     # Full daily pipeline orchestrator
├── pipeline/
│   ├── mqtt_subscriber.py      # MQTT → InfluxDB writer (runs as systemd service)
│   ├── aggregator.py           # Daily Pandas aggregation + SOC prediction
│   ├── validator.py            # SOC sanity checks
│   └── test_aggregator.py      # Quick data verification script
├── model/
│   ├── generate_data.py        # Synthetic SOC training data generator
│   ├── train.py                # Random Forest training script
│   └── soc_model.pkl           # Trained model (not committed to git)
├── oracle/
│   └── signer.py               # SHA-256 hash + web3.py signing + mint
├── contract/
│   ├── CarbonCredit.sol        # ERC-721 smart contract
│   └── abi.json                # Contract ABI
├── data/                       # Daily aggregates CSV (not committed to git)
├── requirements.txt
└── .env                        # Secrets (not committed to git)
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/yourusername/Agri-chain.git
cd Agri-chain
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure `.env`

```dotenv
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=your_influxdb_token
INFLUX_ORG=agrichain
INFLUX_BUCKET=farm_sensors

SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/your_project_id
CONTRACT_ADDRESS=your_contract_address
FARMER_ADDRESS=your_metamask_wallet_address

DEVICE_ADDRESS=your_pi_wallet_address
DEVICE_PRIVATE_KEY=your_pi_private_key

MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_TOPIC=farm/sensors
```

### 3. Start MQTT subscriber as a service

```bash
sudo systemctl enable agrichain-subscriber
sudo systemctl start agrichain-subscriber
```

### 4. Schedule daily pipeline

```bash
crontab -e
```

Add:
```
0 23 * * * /home/dc/Agri-chain/venv/bin/python3 /home/dc/Agri-chain/main.py
```

---

## Smart Contract

- **Network**: Ethereum Sepolia Testnet
- **Standard**: ERC-721 (NFT)
- **Token Name**: AgriChain Carbon Credit (AGCC)
- **Functions**:
  - `registerDevice(address)` — owner registers a Pi device
  - `verify(dataHash, signature, device)` — validates Pi signature
  - `mint(farmer, device, nodeId, socPercent, dataHash, signature)` — mints NFT if SOC increased

---

## Verification

Each carbon credit NFT can be independently verified:

1. **Blockchain** — look up token on [Sepolia Etherscan](https://sepolia.etherscan.io)
2. **Data integrity** — recompute SHA-256 hash of raw sensor data and compare with on-chain hash
3. **Device identity** — confirm signature was produced by a registered Pi device

---

## SOC Model

- **Algorithm**: Random Forest Regressor (scikit-learn)
- **Features**: avg_temperature, avg_humidity, avg_soil_moisture, env_stress
- **Output**: SOC% (0.3% – 2.5%, realistic Indian farmland range)
- **Validation**: SOC cannot change more than 0.5% per day

---

## License

MIT
