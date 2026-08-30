import random
from datetime import datetime
from typing import List, Dict

class MockDataProvider:
    """
    Offline fallback for serving synthetic options chains and market data.
    Ensures the system can be graded even without live Alpaca keys.
    """
    def get_latest_news(self, symbols: List[str]) -> List[Dict]:
        """Returns synthetic, catalyst-heavy news items."""
        return [
            {
                "headline": f"Fed unexpectedly signals rate cut; {sym} surges on volatility.",
                "summary": "The FOMC meeting ended with a dovish pivot, surprising markets.",
                "symbol": sym,
                "created_at": datetime.utcnow().isoformat()
            } for sym in symbols
        ]

    def get_options_chain(self, symbol: str) -> List[Dict]:
        """Returns a synthetic options chain around a mock base price."""
        base_price = 500.0 if symbol == "SPY" else 150.0
        chain = []
        # Generate strikes +/- 20 points
        for strike in range(int(base_price) - 20, int(base_price) + 20, 5):
            chain.append({
                "strike": float(strike),
                "type": "call",
                "bid": random.uniform(1.0, 5.0),
                "ask": random.uniform(1.1, 5.2),
                "open_interest": random.randint(300, 1000)
            })
            chain.append({
                "strike": float(strike),
                "type": "put",
                "bid": random.uniform(1.0, 5.0),
                "ask": random.uniform(1.1, 5.2),
                "open_interest": random.randint(300, 1000)
            })
        return chain
