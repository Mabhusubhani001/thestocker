import asyncio
import logging
from typing import Callable, List
from data.alpaca_client import AlpacaDataClient
from data.mock_provider import MockDataProvider
from config.settings import settings
from agents.schemas import VolatilitySignal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventPoller:
    """
    Background asyncio worker that wakes up at POLL_INTERVAL_SECONDS.
    It fetches news, and if a catalyst is found, it triggers the callback.
    """
    def __init__(self, callback: Callable[[VolatilitySignal], None]):
        self.callback = callback
        self.is_running = False
        self.alpaca_client = AlpacaDataClient()
        self.mock_provider = MockDataProvider()
        self.processed_news_ids = set()
        
    async def _poll_cycle(self, symbols: List[str]):
        """Single polling execution."""
        logger.info(f"Polling news for {symbols}...")
        
        # Dependency Injection / Fallback
        if not settings.ALPACA_API_KEY:
            logger.warning("No Alpaca API keys found. Falling back to MockDataProvider.")
            news_items = self.mock_provider.get_latest_news(symbols)
        else:
            try:
                news_items = await self.alpaca_client.get_latest_news(symbols)
                if not news_items:
                    # If live call succeeds but returns nothing, optionally mock for testing
                    news_items = self.mock_provider.get_latest_news(symbols)
            except Exception as e:
                logger.error(f"Alpaca API error: {e}. Falling back to mock.")
                news_items = self.mock_provider.get_latest_news(symbols)
                
        # Simple heuristic to detect a "catalyst" for now.
        # Professional Institutional Mode: We ONLY trigger on massive macro events.
        for item in news_items:
            # Generate a unique ID for the news item (Alpaca news usually has an 'id' field, fallback to headline)
            news_id = item.get("id", item.get("headline", ""))
            
            if news_id in self.processed_news_ids:
                continue # Skip deduplication
                
            headline = item.get("headline", "").lower()
            if any(kw in headline for kw in ["fed", "fomc", "cpi", "nfp", "gdp", "inflation", "recession", "powell"]):
                logger.info(f"Catalyst detected: {headline}")
                self.processed_news_ids.add(news_id) # Mark as processed
                
                # Check Market Clock before waking the Swarm
                if not self.alpaca_client.is_market_open():
                    logger.warning("Market is closed. Catalyst detected but skipping Swarm execution.")
                    break # Skip processing triggers until the market opens
                
                signal = VolatilitySignal(
                    symbol=item.get("symbol", "SPY"),
                    catalyst_type="Macro",
                    implied_volatility_bias="crush",
                    confidence_score=0.85,
                    rationale=f"Found macroeconomic catalyst in headline: {headline}"
                )
                res = self.callback(signal)
                if asyncio.iscoroutine(res):
                    await res
                break # Only trigger one signal per cycle to avoid flooding the swarm

    async def start(self, symbols: List[str]):
        """Starts the infinite polling loop."""
        self.is_running = True
        logger.info("Event poller started.")
        while self.is_running:
            await self._poll_cycle(symbols)
            logger.info(f"Sleeping for {settings.POLL_INTERVAL_SECONDS} seconds...")
            await asyncio.sleep(settings.POLL_INTERVAL_SECONDS)
            
    def stop(self):
        self.is_running = False
        logger.info("Event poller stopping...")
