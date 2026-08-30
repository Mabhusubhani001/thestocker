import httpx
from typing import List, Dict
from config.settings import settings

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
