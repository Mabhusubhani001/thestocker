from abc import ABC, abstractmethod
import uuid
from agents.schemas import TradeProposal

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
