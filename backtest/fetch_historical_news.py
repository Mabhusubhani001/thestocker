import os
import json
import requests
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Load Alpaca keys
load_dotenv()
API_KEY = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_SECRET_KEY")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
EPISODIC_DIR = os.path.join(DATA_DIR, 'episodic')

# 5 High-Impact Market Days from 2024
DATES = [
    "2024-04-10", # CPI Hot
    "2024-07-24", # Tech Selloff
    "2024-08-02", # Bad Jobs Report
    "2024-08-05", # Yen Carry Trade Crash
    "2024-08-14"  # CPI Cool
]

TICKERS = ["SPY", "QQQ"]

def fetch_historical_news():
    os.makedirs(EPISODIC_DIR, exist_ok=True)
    
    headers = {
        "Apca-Api-Key-Id": API_KEY,
        "Apca-Api-Secret-Key": API_SECRET
    }
    
    print("Fetching historical news for episodic backtest...")
    
    all_news = {}
    
    for date_str in DATES:
        print(f"Fetching news for {date_str}...")
        start_time = f"{date_str}T00:00:00Z"
        end_time = f"{date_str}T23:59:59Z"
        
        symbols = ",".join(TICKERS)
        url = f"https://data.alpaca.markets/v1beta1/news?start={start_time}&end={end_time}&symbols={symbols}&limit=10"
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            all_news[date_str] = data.get("news", [])
            print(f"  -> Found {len(all_news[date_str])} articles.")
        else:
            print(f"  -> Error: {response.text}")
            all_news[date_str] = []
            
    cache_path = os.path.join(EPISODIC_DIR, "news_cache.json")
    with open(cache_path, "w") as f:
        json.dump(all_news, f, indent=4)
        
    print(f"Cached historical news to {cache_path}")

if __name__ == "__main__":
    fetch_historical_news()
