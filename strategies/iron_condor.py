from strategies.base import OptionsStrategy
from agents.schemas import TradeProposal, OptionsLeg
from datetime import datetime, timedelta

class IronCondorStrategy(OptionsStrategy):
    """
    Constructs an Iron Condor: A defined-risk, delta-neutral strategy 
    designed to profit from IV crush and time decay (Theta).
    
    Consists of:
    - Short Call & Short Put (collect premium)
    - Long Call & Long Put (cap maximum loss)
    """
    def construct_proposal(self) -> TradeProposal:
        # In a live system, this would scan the real options chain from Alpaca API.
        # For this autonomous agent system, we algorithmically select strikes based on current price.
        
        # Algorithm: Set strikes roughly 5% away for the shorts, and 10% away for the longs.
        short_put_strike = round(self.current_price * 0.95, 2)
        long_put_strike = round(self.current_price * 0.90, 2)
        
        short_call_strike = round(self.current_price * 1.05, 2)
        long_call_strike = round(self.current_price * 1.10, 2)
        
        # Expiration target: ~30 days out
        expiration = (datetime.utcnow() + timedelta(days=30)).date()
        
        legs = [
            OptionsLeg(contract_symbol=f"{self.symbol}_LONG_PUT", strike=long_put_strike, expiration=expiration, option_type="put", side="buy", ratio=1),
            OptionsLeg(contract_symbol=f"{self.symbol}_SHORT_PUT", strike=short_put_strike, expiration=expiration, option_type="put", side="sell", ratio=1),
            OptionsLeg(contract_symbol=f"{self.symbol}_SHORT_CALL", strike=short_call_strike, expiration=expiration, option_type="call", side="sell", ratio=1),
            OptionsLeg(contract_symbol=f"{self.symbol}_LONG_CALL", strike=long_call_strike, expiration=expiration, option_type="call", side="buy", ratio=1),
        ]
        
        # Calculate Risk/Reward
        wing_width = abs(long_call_strike - short_call_strike)
        net_credit = 2.50 # Synthetic premium collected (e.g. $250 total per contract)
        max_loss = wing_width - net_credit
        
        return TradeProposal(
            proposal_id=self._generate_id(),
            symbol=self.symbol,
            strategy_name="Iron Condor",
            legs=legs,
            net_credit=net_credit,
            max_loss=max_loss,
            iv_rank=self.iv_rank,
            delta_exposure=0.0  # Ideally Delta Neutral
        )
