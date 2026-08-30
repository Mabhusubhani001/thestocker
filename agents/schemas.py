from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime, date

class VolatilitySignal(BaseModel):
    """
    Data contract emitted by the Event/Narrative engine indicating a potential volatility play.
    """
    symbol: str = Field(..., description="The underlying ticker symbol (e.g., SPY).")
    catalyst_type: str = Field(..., description="Type of catalyst (e.g., Earnings, FOMC, CPI).")
    implied_volatility_bias: Literal["expansion", "crush", "neutral"] = Field(
        ..., description="Expected direction of implied volatility."
    )
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Agent's confidence in the signal.")
    rationale: str = Field(..., description="Detailed explanation of the signal.")

class OptionsLeg(BaseModel):
    """
    Data contract for a single option leg within a strategy structure.
    """
    contract_symbol: str = Field(..., description="The OCC contract symbol.")
    strike: float = Field(..., description="The strike price of the option.")
    expiration: date = Field(..., description="The expiration date of the option.")
    option_type: Literal["call", "put"] = Field(..., description="Type of option.")
    side: Literal["buy", "sell"] = Field(..., description="Action to take on the leg.")
    ratio: int = Field(..., gt=0, description="Ratio of this leg in the strategy structure.")

class TradeProposal(BaseModel):
    """
    Data contract for a fully constructed trade proposed by the Quant Agent.
    """
    proposal_id: str = Field(..., description="Unique identifier for the proposal.")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Time the proposal was generated.")
    symbol: str = Field(..., description="The underlying ticker symbol.")
    strategy_name: str = Field(..., description="Name of the strategy (e.g., Iron Condor, Credit Spread).")
    legs: List[OptionsLeg] = Field(..., min_length=1, description="List of option legs comprising the trade.")
    net_credit: float = Field(..., description="Total net credit collected (or debit paid if negative).")
    max_loss: float = Field(..., description="Maximum possible loss for the structure.")
    iv_rank: float = Field(..., ge=0.0, le=100.0, description="Current Implied Volatility Rank (IVR).")
    delta_exposure: float = Field(..., description="Net portfolio delta exposure of the structure.")

class CriticDecision(BaseModel):
    """
    Data contract for the Adversarial Critic Agent's final decision on a trade proposal.
    """
    proposal_id: str = Field(..., description="The ID of the trade proposal being evaluated.")
    is_approved: bool = Field(..., description="Whether the trade is approved for execution.")
    rejection_reason: Optional[str] = Field(None, description="Detailed reason if the trade is rejected.")
