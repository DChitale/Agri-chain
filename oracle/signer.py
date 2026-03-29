# SHA-256 hash + web3.py signing
# This script handles SHA-256 hashing and signing attestations using web3.py.
import os
import json
import hashlib
import pandas as pd
from web3 import Web3
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

SEPOLIA_RPC_URL  = os.getenv("SEPOLIA_RPC_URL")
DEVICE_ADDRESS   = os.getenv("DEVICE_ADDRESS")
DEVICE_PRIVATE_KEY = os.getenv("DEVICE_PRIVATE_KEY")
FARMER_ADDRESS   = os.getenv("FARMER_ADDRESS")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

with open("contract/abi.json") as f:
    ABI = json.load(f)

w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))
contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=ABI)

def hash_sensor_data(data: dict) -> bytes:
    raw = json.dumps(data, sort_keys=True).encode()
    return hashlib.sha256(raw).digest()

def sign_data(data_hash: bytes) -> bytes:
    signed = w3.eth.account.sign_message(
        signable_message=__import__('eth_account').messages.encode_defunct(data_hash),
        private_key=DEVICE_PRIVATE_KEY
    )
    return signed.signature

def mint_carbon_credit(soc_percent: float, sensor_data: dict):
    data_hash  = hash_sensor_data(sensor_data)
    signature  = sign_data(data_hash)
    soc_scaled = int(soc_percent * 1000)  # e.g. 1.250% → 1250

    nonce = w3.eth.get_transaction_count(Web3.to_checksum_address(DEVICE_ADDRESS))

    txn = contract.functions.mint(
        Web3.to_checksum_address(FARMER_ADDRESS),
        Web3.to_checksum_address(DEVICE_ADDRESS),
        sensor_data.get("node_id", "node_01"),
        soc_scaled,
        data_hash,
        signature
    ).build_transaction({
        "from":     Web3.to_checksum_address(DEVICE_ADDRESS),
        "nonce":    nonce,
        "gas":      300000,
        "gasPrice": w3.eth.gas_price,
    })

    signed_txn = w3.eth.account.sign_transaction(txn, private_key=DEVICE_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

    print(f"[+] TX sent: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"[+] Confirmed in block: {receipt.blockNumber}")
    return tx_hash.hex()

if __name__ == "__main__":
    # Test with latest aggregated data
    df = pd.read_csv("data/daily_aggregates.csv")
    latest = df.iloc[-1].to_dict()

    sensor_data = {
        "node_id":          "node_01",
        "date":             latest["date"],
        "avg_temperature":  latest["avg_temperature"],
        "avg_humidity":     latest["avg_humidity"],
        "avg_soil_moisture":latest["avg_soil_moisture"],
        "env_stress":       latest["env_stress"],
    }

    soc = latest["soc_percent"]
    print(f"[+] SOC: {soc}%")
    mint_carbon_credit(soc, sensor_data)