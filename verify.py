import os
import requests
from dotenv import load_dotenv

# Load your Alpaca Keys from .env
load_dotenv()
HEADERS = {
    "APCA-API-KEY-ID": os.getenv("ALPACA_API_KEY"),
    "APCA-API-SECRET-KEY": os.getenv("ALPACA_SECRET_KEY"),
    "accept": "application/json"
}

print("=== 1. VERIFYING LIVE NEWS ===")
news_url = "https://data.alpaca.markets/v1beta1/news?symbols=SPY&limit=3"
news_response = requests.get(news_url, headers=HEADERS)
for article in news_response.json().get('news', []):
    print(f"- [{article['created_at']}] {article['headline']}")

print("\n=== 2. VERIFYING LIVE OPTIONS SYMBOLS ===")
options_url = "https://paper-api.alpaca.markets/v2/options/contracts?underlying_symbols=SPY&status=active&limit=5"
options_response = requests.get(options_url, headers=HEADERS)
for contract in options_response.json().get('option_contracts', []):
    print(f"- Symbol: {contract['symbol']} | Type: {contract['type']} | Strike: ${contract['strike_price']} | Exp: {contract['expiration_date']}")