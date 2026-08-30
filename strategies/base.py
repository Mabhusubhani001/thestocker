from abc import ABC, abstractmethod
import uuid
from typing import List, Tuple
from datetime import datetime
from agents.schemas import TradeProposal, OptionsLeg
from data.alpaca_client import AlpacaDataClient
from features.greeks import calculate_black_scholes

class OptionsStrategy(ABC):
    """
    Abstract Base Class for Options Strategy Constructors.
    Enforces a strict contract: all strategies must yield a standardized TradeProposal.
    """
    def __init__(self, symbol: str, current_price: float, iv_rank: float):
        self.symbol = symbol
        self.current_price = current_price
        self.iv_rank = iv_rank
        
    @abstractmethod
    def construct_proposal(self) -> TradeProposal:
        """Constructs and returns the TradeProposal for the strategy."""
        pass
        
    def _generate_id(self) -> str:
        """Generates a unique proposal ID."""
        return f"PROPOSAL-{uuid.uuid4().hex[:8].upper()}"

    def calculate_live_metrics(self, legs: List[OptionsLeg], strategy_type: str = "credit") -> Tuple[float, float, float]:
        """
        Fetches live option quotes and computes the true net_credit, max_loss, and portfolio delta.
        Returns (net_credit, max_loss, delta_exposure).
        """
        client = AlpacaDataClient()
        contract_symbols = [leg.contract_symbol for leg in legs]
        live_quotes = client.get_option_snapshot(contract_symbols)
        
        net_credit = 0.0
        net_delta = 0.0
        
        # Risk-free rate and assumed IV for Black-Scholes if not provided by exchange
        r = 0.05
        sigma = 0.25 
        
        for i, leg in enumerate(legs):
            quote = live_quotes[i]
            ask = quote.get("ask", 0.0)
            bid = quote.get("bid", 0.0)
            
            # 1. Calculate Premium
            if leg.side == "buy":
                price = ask if ask > 0 else 1.00 # Fallback
                net_credit -= (price * leg.ratio)
            else:
                price = bid if bid > 0 else 1.00 # Fallback
                net_credit += (price * leg.ratio)
                
            # 2. Calculate Black-Scholes Delta
            days_to_expiry = (leg.expiration - datetime.utcnow().date()).days
            T = max(1, days_to_expiry) / 365.0
            
            greeks = calculate_black_scholes(
                S=self.current_price,
                K=leg.strike,
                T=T,
                r=r,
                sigma=sigma,
                option_type=leg.option_type
            )
            
            leg_delta = greeks["delta"] * leg.ratio
            if leg.side == "sell":
                leg_delta = -leg_delta
                
            net_delta += leg_delta

        # 3. Calculate Max Loss based on strategy type
        max_loss = 0.0
        if strategy_type == "iron_condor":
            # Wing width minus net credit
            calls = [l for l in legs if l.option_type == "call"]
            puts = [l for l in legs if l.option_type == "put"]
            call_width = abs(calls[0].strike - calls[1].strike) if len(calls) == 2 else 0
            put_width = abs(puts[0].strike - puts[1].strike) if len(puts) == 2 else 0
            wing_width = max(call_width, put_width)
            max_loss = wing_width - net_credit
        elif strategy_type == "straddle":
            # For a long straddle, max loss is the debit paid
            max_loss = abs(net_credit) if net_credit < 0 else 0.0
        elif strategy_type == "credit_spread":
            width = abs(legs[0].strike - legs[1].strike)
            max_loss = width - net_credit
            
        return round(net_credit, 2), round(max_loss, 2), round(net_delta, 4)
