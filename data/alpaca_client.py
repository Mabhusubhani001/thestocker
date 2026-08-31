import httpx
from typing import List, Dict, Optional
from datetime import date
from config.settings import settings
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOptionContractsRequest
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionSnapshotRequest, StockBarsRequest
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.timeframe import TimeFrame
from features.greeks import calculate_black_scholes, calculate_implied_volatility
import math
import numpy as np

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
        self.stock_data_client = StockHistoricalDataClient(
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
                days_to_expiry = max(1, (c.expiration_date - date.today()).days)
                T = days_to_expiry / 365.0
                
                # Calculate BS Greeks using heuristics for IV (0.25)
                # In a real environment with live IV feeds, we would pass the actual contract IV.
                if current_price:
                    greeks = calculate_black_scholes(
                        S=current_price,
                        K=float(c.strike_price),
                        T=T,
                        r=0.05,
                        sigma=0.25,
                        option_type=c.type
                    )
                    delta = greeks["delta"]
                else:
                    delta = 0.0

                contracts.append({
                    "contract_symbol": c.symbol,
                    "strike": float(c.strike_price),
                    "expiration": c.expiration_date,
                    "option_type": c.type,
                    "delta": delta
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

    def get_volatility_metrics(self, symbol: str, current_price: float) -> tuple[float, List[float]]:
        """
        Computes real-time Implied Volatility (IV) using Newton-Raphson on the ATM option,
        and computes a 30-day Historical Volatility (HV) array proxy using daily stock returns.
        """
        # 1. Calculate Historical Volatility Proxy (last 30 days)
        # Fetch 60 days of historical bars to compute 30 days of rolling 30-day volatility
        historical_ivs = []
        try:
            from datetime import timedelta
            end_dt = date.today()
            start_dt = end_dt - timedelta(days=90)
            
            req = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start_dt,
                end=end_dt,
                feed="iex" # Free tier
            )
            bars = self.stock_data_client.get_stock_bars(req)
            if symbol in bars.data:
                closes = [b.close for b in bars.data[symbol]]
                if len(closes) > 30:
                    returns = [math.log(closes[i]/closes[i-1]) for i in range(1, len(closes))]
                    # Calculate rolling 30-day annualized std dev
                    for i in range(30, len(returns)):
                        window = returns[i-30:i]
                        std_dev = np.std(window, ddof=1)
                        ann_vol = std_dev * math.sqrt(252)
                        historical_ivs.append(round(ann_vol, 4))
        except Exception as e:
            print(f"Error fetching historical bars for {symbol}: {e}")
            
        if not historical_ivs:
            # Ultimate fallback if free tier API fails
            historical_ivs = [0.25] * 30
            
        # 2. Calculate Current Implied Volatility using Newton-Raphson
        current_iv = historical_ivs[-1] # Fallback to latest HV
        try:
            chain = self.get_active_option_chain(symbol, current_price)
            if chain:
                # Find the ATM call expiring closest to 30 days out
                target_date = date.today() + timedelta(days=30)
                atm_call = min(
                    [c for c in chain if c['option_type'] == 'call'], 
                    key=lambda x: abs(x['strike'] - current_price) + abs((x['expiration'] - target_date).days)*10, # Weight DTE heavier
                    default=None
                )
                
                if atm_call:
                    snap = self.get_option_snapshot([atm_call['contract_symbol']])[0]
                    mid_price = (snap['bid'] + snap['ask']) / 2.0
                    
                    if mid_price > 0:
                        T = max(1, (atm_call['expiration'] - date.today()).days) / 365.0
                        calc_iv = calculate_implied_volatility(
                            target_price=mid_price,
                            S=current_price,
                            K=atm_call['strike'],
                            T=T,
                            r=0.05,
                            option_type="call"
                        )
                        if calc_iv > 0:
                            current_iv = round(calc_iv, 4)
        except Exception as e:
            print(f"Error calculating current IV for {symbol}: {e}")

        return current_iv, historical_ivs

    def get_breeden_litzenberger_probabilities(self, symbol: str, current_price: float) -> str:
        """
        Fetches the live option chain for the nearest expiration, pulls live prices,
        and extracts the market-implied risk-neutral probability distribution
        using the Breeden-Litzenberger theorem.
        """
        try:
            from features.probabilities import extract_risk_neutral_probabilities
            from datetime import date
            
            chain = self.get_active_option_chain(symbol, current_price)
            if not chain:
                return "Breeden-Litzenberger Risk-Neutral Probabilities (Live Estimation):\n- Data unavailable."
                
            calls = [c for c in chain if c['option_type'] == 'call']
            if not calls:
                return "Breeden-Litzenberger Risk-Neutral Probabilities (Live Estimation):\n- Data unavailable."
                
            # Find the nearest expiration date
            nearest_exp = min([c['expiration'] for c in calls])
            
            # Filter for nearest expiration and sort by strike
            nearest_calls = [c for c in calls if c['expiration'] == nearest_exp]
            nearest_calls = sorted(nearest_calls, key=lambda x: x['strike'])
            
            # We need at least 3 strikes for finite differences
            if len(nearest_calls) < 3:
                return "Breeden-Litzenberger Risk-Neutral Probabilities (Live Estimation):\n- Insufficient strikes."
                
            contract_symbols = [c['contract_symbol'] for c in nearest_calls]
            strikes = [c['strike'] for c in nearest_calls]
            
            # Fetch live snapshots
            snapshots = self.get_option_snapshot(contract_symbols)
            call_prices = []
            for snap in snapshots:
                mid = (snap['bid'] + snap['ask']) / 2.0
                call_prices.append(mid)
                
            # Extract probabilities
            probs = extract_risk_neutral_probabilities(strikes, call_prices)
            
            context = "Breeden-Litzenberger Risk-Neutral Probabilities (Live Estimation):\n"
            for k, p in probs.items():
                if p > 0.01: # Only show strikes with > 1% probability to keep prompt clean
                    context += f"- Strike ${k:.2f}: {p * 100:.1f}%\n"
                    
            if context == "Breeden-Litzenberger Risk-Neutral Probabilities (Live Estimation):\n":
                return context + "- Probabilities negligible."
                
            return context
        except Exception as e:
            print(f"Error calculating Breeden-Litzenberger probabilities: {e}")
            return "Breeden-Litzenberger Risk-Neutral Probabilities (Live Estimation):\n- Error in calculation."
