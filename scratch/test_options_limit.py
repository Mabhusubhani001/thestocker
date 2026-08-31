import os
import sys
from pathlib import Path
from datetime import date, timedelta

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOptionContractsRequest

def test_option_contracts():
    client = TradingClient(settings.ALPACA_API_KEY, settings.ALPACA_SECRET_KEY, paper=settings.ALPACA_PAPER)
    
    current_price = 766.0
    req = GetOptionContractsRequest(
        underlying_symbols=["SPY"],
        status="active",
        strike_price_gte=str(round(current_price * 0.85, 2)),
        strike_price_lte=str(round(current_price * 1.15, 2)),
        limit=10000
    )
    
    res = client.get_option_contracts(req)
    print(f"Found {len(res.option_contracts)} contracts.")
    if len(res.option_contracts) > 0:
        max_exp = max(c.expiration_date for c in res.option_contracts)
        print(f"Max expiration date returned: {max_exp}")
        
        min_date = date.today() + timedelta(days=14)
        valid_contracts = [c for c in res.option_contracts if c.expiration_date >= min_date]
        print(f"Contracts matching >= {min_date}: {len(valid_contracts)}")

if __name__ == "__main__":
    test_option_contracts()
