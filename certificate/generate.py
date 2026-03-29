import os
import sys
import json
import qrcode
import tempfile
from web3 import Web3
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

load_dotenv()

SEPOLIA_RPC_URL  = os.getenv("SEPOLIA_RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

with open("contract/abi.json") as f:
    ABI = json.load(f)

w3       = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))
contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=ABI)

def fetch_credit(token_id: int) -> dict:
    data = contract.functions.credits(token_id).call()
    owner = contract.functions.ownerOf(token_id).call()
    return {
        "token_id":    token_id,
        "node_id":     data[0],
        "timestamp":   data[1],
        "soc_percent": data[2] / 1000,
        "previous_soc":data[3] / 1000,
        "data_hash":   "0x" + data[4].hex(),
        "co2_tonnes":  data[5] / 1000,
        "owner":       owner,
    }

def make_qr(token_id: int) -> str:
    tx_url = f"https://sepolia.etherscan.io/token/{CONTRACT_ADDRESS}?a={token_id}"
    img = qrcode.make(tx_url)
    tmp = tempfile.mktemp(suffix=".png")
    img.save(tmp)
    return tmp

def generate_certificate(token_id: int):
    credit = fetch_credit(token_id)
    qr_path = make_qr(token_id)

    from datetime import datetime, timezone
    date_str = datetime.fromtimestamp(credit["timestamp"], tz=timezone.utc).strftime("%B %d, %Y")

    os.makedirs("certificates", exist_ok=True)
    output_path = f"certificates/certificate_token_{token_id}.pdf"

    W, H = A4
    c = canvas.Canvas(output_path, pagesize=A4)

    # Background
    c.setFillColorRGB(0.97, 0.97, 0.95)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Green header bar
    c.setFillColorRGB(0.18, 0.49, 0.20)
    c.rect(0, H - 60*mm, W, 60*mm, fill=1, stroke=0)

    # Title
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(W / 2, H - 28*mm, "AgriChain Carbon Credit Certificate")
    c.setFont("Helvetica", 13)
    c.drawCentredString(W / 2, H - 42*mm, "Verified Soil Organic Carbon Sequestration")

    # Token ID badge
    c.setFillColorRGB(0.18, 0.49, 0.20)
    c.roundRect(W/2 - 30*mm, H - 75*mm, 60*mm, 18*mm, 4*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W / 2, H - 64*mm, f"Token ID: #{token_id}")

    # Main data fields
    def draw_field(label, value, y):
        c.setFillColorRGB(0.3, 0.3, 0.3)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(25*mm, y, label)
        c.setFillColorRGB(0.1, 0.1, 0.1)
        c.setFont("Helvetica", 10)
        c.drawString(80*mm, y, str(value))
        c.setStrokeColorRGB(0.85, 0.85, 0.85)
        c.line(25*mm, y - 2*mm, W - 25*mm, y - 2*mm)

    y = H - 95*mm
    gap = 14*mm
    draw_field("Date Issued",        date_str,                              y)
    draw_field("Farmer Wallet",      credit["owner"],                       y - gap)
    draw_field("Sensor Node",        credit["node_id"],                     y - 2*gap)
    draw_field("SOC Percentage",     f"{credit['soc_percent']:.3f}%",       y - 3*gap)
    draw_field("Previous SOC",       f"{credit['previous_soc']:.3f}%",      y - 4*gap)
    draw_field("CO2 Sequestered",    f"{credit['co2_tonnes']:.3f} tonnes",  y - 5*gap)
    draw_field("Contract Address",   CONTRACT_ADDRESS,                      y - 6*gap)

    # Data hash (truncated)
    short_hash = credit["data_hash"][:24] + "..." + credit["data_hash"][-8:]
    draw_field("Data Hash (SHA-256)", short_hash,                           y - 7*gap)

    # QR code
    qr_y = 28*mm
    c.drawImage(qr_path, W - 65*mm, qr_y, width=40*mm, height=40*mm)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.setFont("Helvetica", 7)
    c.drawCentredString(W - 45*mm, qr_y - 4*mm, "Scan to verify on Etherscan")

    # Footer
    c.setFillColorRGB(0.18, 0.49, 0.20)
    c.rect(0, 0, W, 18*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 8)
    c.drawCentredString(W / 2, 10*mm, f"Ethereum Sepolia Testnet  |  {CONTRACT_ADDRESS}  |  Agri-chain")

    c.save()
    os.remove(qr_path)
    print(f"[+] Certificate saved: {output_path}")
    return output_path

if __name__ == "__main__":
    token_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    generate_certificate(token_id)