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
    
    req = GetOptionContractsRequest(
        underlying_symbols=["SPY"],
        status="active",
        limit=10000
    )
    
    # We will paginate to get ALL contracts and find the max expiration
    contracts = []
    page_token = None
    
    while True:
        if page_token:
            req.page_token = page_token
            
        res = client.get_option_contracts(req)
        contracts.extend(res.option_contracts)
        
        if getattr(res, 'next_page_token', None):
            page_token = res.next_page_token
        else:
            break
            
    print(f"Found total {len(contracts)} contracts across all pages.")
    if len(contracts) > 0:
        max_exp = max(c.expiration_date for c in contracts)
        min_exp = min(c.expiration_date for c in contracts)
        print(f"Min expiration date returned: {min_exp}")
        print(f"Max expiration date returned: {max_exp}")
        
        min_date = date.today() + timedelta(days=14)
        valid_contracts = [c for c in contracts if c.expiration_date >= min_date]
        print(f"Contracts matching >= {min_date}: {len(valid_contracts)}")

if __name__ == "__main__":
    test_option_contracts()
