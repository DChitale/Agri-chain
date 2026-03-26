"""
Agri-chain Oracle Script
Main "Brain" - Combines AI (Scikit-learn) with Web3 (Blockchain) logic
"""

import os
import pickle
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AgriChainOracle:
    def __init__(self):
        """Initialize the oracle with blockchain and AI components"""
        self.sepolia_rpc_url = os.getenv('SEPOLIA_RPC_URL')
        self.private_key = os.getenv('PRIVATE_KEY')
        self.model = None
        self.load_model()
    
    def load_model(self):
        """Load the trained Scikit-learn model"""
        try:
            with open('models/soc_model.pkl', 'rb') as f:
                self.model = pickle.load(f)
            print("Model loaded successfully")
        except FileNotFoundError:
            print("Model file not found. Please train the model first.")
    
    def predict(self, data):
        """Make predictions using the trained model"""
        if self.model is None:
            raise ValueError("Model not loaded")
        return self.model.predict(data)
    
    def run(self):
        """Main oracle execution loop"""
        print("Agri-chain Oracle started...")
        # Add your main logic here

if __name__ == "__main__":
    oracle = AgriChainOracle()
    oracle.run()
