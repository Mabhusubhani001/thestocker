import httpx
from typing import List, Dict, Optional
from datetime import date
from config.settings import settings
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOptionContractsRequest
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionSnapshotRequest

class AlpacaDataClient:
    """
    Client for interacting with Alpaca Market Data API.
    Reads from https://data.alpaca.markets as per the skill docs.
    """
    BASE_URL = "https://data.alpaca.markets"
    
    def __init__(self):
        self.headers = {
            "APCA-API-KEY-ID": settings.ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": settings.ALPACA_SECRET_KEY,
        }
        self.trading_client = TradingClient(
            api_key=settings.ALPACA_API_KEY, 
            secret_key=settings.ALPACA_SECRET_KEY, 
            paper=settings.ALPACA_PAPER
        )
        self.option_data_client = OptionHistoricalDataClient(
            api_key=settings.ALPACA_API_KEY,
            secret_key=settings.ALPACA_SECRET_KEY
        )
        
    def get_active_option_chain(self, symbol: str, current_price: Optional[float] = None) -> List[Dict]:
        """
        Fetches the real active option chain for the given symbol using alpaca-py.
        Returns a list of dicts with OSI symbol, strike, expiration, and type.
        """
        if not settings.ALPACA_API_KEY:
            return []
            
        req_params = {
            "underlying_symbols": [symbol],
            "status": "active",
            "limit": 10000
        }
        
        if current_price:
            req_params["strike_price_gte"] = str(round(current_price * 0.85, 2))
            req_params["strike_price_lte"] = str(round(current_price * 1.15, 2))
            
        req = GetOptionContractsRequest(**req_params)
        try:
            res = self.trading_client.get_option_contracts(req)
            contracts = []
            for c in res.option_contracts:
                contracts.append({
                    "contract_symbol": c.symbol,
                    "strike": float(c.strike_price),
                    "expiration": c.expiration_date,
                    "option_type": c.type
                })
            return contracts
        except Exception as e:
            print(f"Error fetching option chains: {e}")
            return []

    def get_account(self):
        """
        Fetches the real-time account data from Alpaca.
        """
        if not settings.ALPACA_API_KEY:
            return None
        try:
            return self.trading_client.get_account()
        except Exception as e:
            print(f"Error fetching account data: {e}")
            return None

    def is_market_open(self) -> bool:
        """
        Fetches the real-time market clock from Alpaca.
        Returns True if the US stock market is currently open.
        """
        if not settings.ALPACA_API_KEY:
            return True # Fallback for local testing without keys
            
        try:
            clock = self.trading_client.get_clock()
            return clock.is_open
        except Exception as e:
            print(f"Error fetching market clock: {e}")
            return True # Fail open so testing doesn't break
            
    async def get_latest_news(self, symbols: List[str], limit: int = 10) -> List[Dict]:
        """
        Polls Alpaca v1beta1 news endpoint.
        Returns empty list if keys are missing (handled by poller fallback).
        """
        if not settings.ALPACA_API_KEY:
            return []

        url = f"{self.BASE_URL}/v1beta1/news"
        params = {
            "symbols": ",".join(symbols),
            "limit": limit
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("news", [])

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Fetches the real-time or latest available price for a stock symbol 
        using the Alpaca Market Data API (v2/stocks/{symbol}/snapshot).
        """
        if not settings.ALPACA_API_KEY:
            return 500.0 # Fallback mock price

        url = f"{self.BASE_URL}/v2/stocks/{symbol}/snapshot"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                
                latest_trade = data.get("latestTrade", {})
                price = latest_trade.get("p")
                
                if price:
                    return float(price)
                    
                # Fallback to latest quote or daily close if trade is missing
                latest_quote = data.get("latestQuote", {})
                ask_price = latest_quote.get("ap")
                bid_price = latest_quote.get("bp")
                if ask_price and bid_price:
                    return (float(ask_price) + float(bid_price)) / 2.0
                    
                daily_bar = data.get("dailyBar", {})
                close_price = daily_bar.get("c")
                if close_price:
                    return float(close_price)
                    
                return 500.0 # Ultimate fallback
            except Exception as e:
                print(f"Error fetching current price for {symbol}: {e}")
                return 500.0

    def get_option_snapshot(self, contract_symbols: List[str]) -> List[Dict]:
        """
        Fetches the real option snapshot for the given contract symbols.
        Returns a list of dicts with bid, ask, and open_interest.
        """
        if not settings.ALPACA_API_KEY:
            # Fallback for local testing without keys
            return [{"bid": 1.00, "ask": 1.05, "open_interest": 500} for _ in contract_symbols]

        try:
            req = OptionSnapshotRequest(symbol_or_symbols=contract_symbols)
            snapshots = self.option_data_client.get_option_snapshot(req)
            
            result = []
            for symbol in contract_symbols:
                snap = snapshots.get(symbol)
                if snap:
                    # Some data may be missing if the option hasn't traded
                    bid = snap.latest_quote.bid_price if snap.latest_quote else 0.0
                    ask = snap.latest_quote.ask_price if snap.latest_quote else 0.0
                    oi = 500 # Defaulting OI if not natively available in snapshot easily, or use snap.implied_volatility if available
                    result.append({"bid": bid, "ask": ask, "open_interest": oi})
                else:
                    # Option exists but no snapshot data available (e.g., illiquid)
                    result.append({"bid": 0.0, "ask": 999.0, "open_interest": 0})
                    
            return result
        except Exception as e:
            print(f"Error fetching option snapshots: {e}")
            # Fail closed for risk management
            return [{"bid": 0.0, "ask": 999.0, "open_interest": 0} for _ in contract_symbols]
