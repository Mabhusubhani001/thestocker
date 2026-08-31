import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOptionContractsRequest
from datetime import date, timedelta

def test_option_contracts():
    print(f"API Key: {settings.ALPACA_API_KEY[:5]}***")
    print(f"Paper: {settings.ALPACA_PAPER}")
    
    client = TradingClient(settings.ALPACA_API_KEY, settings.ALPACA_SECRET_KEY, paper=settings.ALPACA_PAPER)
    
    # 1. Test basic SPY request without strike filters
    print("\n--- Test 1: Basic SPY contracts (limit=5) ---")
    req1 = GetOptionContractsRequest(
        underlying_symbols=["SPY"],
        status="active",
        limit=5
    )
    try:
        res1 = client.get_option_contracts(req1)
        print(f"Found {len(res1.option_contracts)} contracts.")
        for c in res1.option_contracts:
            print(f"Symbol: {c.symbol}, Strike: {c.strike_price}, Exp: {c.expiration_date}")
    except Exception as e:
        print(f"Error 1: {e}")
        
    # 2. Test SPY request with strike filters (like our code)
    print("\n--- Test 2: SPY contracts with strike filter (766 * 0.85 to 1.15) ---")
    current_price = 766.0
    req2 = GetOptionContractsRequest(
        underlying_symbols=["SPY"],
        status="active",
        strike_price_gte=str(round(current_price * 0.85, 2)),
        strike_price_lte=str(round(current_price * 1.15, 2)),
        limit=5
    )
    try:
        res2 = client.get_option_contracts(req2)
        print(f"Found {len(res2.option_contracts)} contracts.")
        for c in res2.option_contracts:
            print(f"Symbol: {c.symbol}, Strike: {c.strike_price}, Exp: {c.expiration_date}")
    except Exception as e:
        print(f"Error 2: {e}")

if __name__ == "__main__":
    test_option_contracts()
