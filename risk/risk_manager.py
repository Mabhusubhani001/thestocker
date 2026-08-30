from typing import Dict, List
from datetime import datetime
from zoneinfo import ZoneInfo
from agents.schemas import TradeProposal, CriticDecision
from config.settings import settings

class RiskManager:
    """
    The 10-Gate Deterministic Risk Engine.
    Acts as the Chief Risk Officer. If any of the 10 invariant gates fail, 
    the TradeProposal is ruthlessly rejected, overriding the LLM agents.
    """
    
    def __init__(self, account_equity: float, daily_start_equity: float, current_margin_used: float, active_positions: List[str]):
        self.account_equity = account_equity
        self.daily_start_equity = daily_start_equity
        self.current_margin_used = current_margin_used
        self.active_positions = active_positions  # List of symbols we already have structures on

    def check_thursday_liquidation(self) -> bool:
        """
        Gate 10: Thursday EOD Liquidation Trigger.
        Checks if it is Thursday and past 15:30 ET.
        """
        tz = ZoneInfo(settings.LIQUIDATION_TIMEZONE)
        now_et = datetime.now(tz)
        
        # In Python datetime, Monday is 0, Thursday is 3
        if now_et.weekday() == settings.LIQUIDATION_DAY_OF_WEEK:
            if now_et.hour > settings.LIQUIDATION_HOUR or \
               (now_et.hour == settings.LIQUIDATION_HOUR and now_et.minute >= settings.LIQUIDATION_MINUTE):
                return True
        return False

    def evaluate_proposal(self, proposal: TradeProposal, leg_market_data: List[Dict]) -> CriticDecision:
        """
        Evaluates the TradeProposal against all 10 Risk Gates.
        `leg_market_data` contains live/mocked quotes (bid, ask, open_interest) for each leg.
        """
        # Gate 10: Hard Liquidation Gate
        if self.check_thursday_liquidation():
            return CriticDecision(
                proposal_id=proposal.proposal_id, 
                is_approved=False, 
                rejection_reason="GATE 10 FAILED: Hard Liquidation active (Past Thu 15:30 ET)."
            )

        # Gate 7: Drawdown Circuit Breaker
        drawdown = (self.daily_start_equity - self.account_equity) / self.daily_start_equity
        if drawdown >= 0.03:
            return CriticDecision(
                proposal_id=proposal.proposal_id, 
                is_approved=False, 
                rejection_reason=f"GATE 7 FAILED: Circuit Breaker triggered. Daily drawdown {drawdown*100:.2f}% >= 3.0%."
            )

        # Gate 6: Max 1 structure per ticker
        if proposal.symbol in self.active_positions:
            return CriticDecision(
                proposal_id=proposal.proposal_id, 
                is_approved=False, 
                rejection_reason=f"GATE 6 FAILED: Already have an active structure on {proposal.symbol}."
            )

        # Gate 1: Max Trade Allocation <= 5%
        max_allowed_risk = self.account_equity * 0.05
        if proposal.max_loss > max_allowed_risk:
            return CriticDecision(
                proposal_id=proposal.proposal_id, 
                is_approved=False, 
                rejection_reason=f"GATE 1 FAILED: Max Loss ${proposal.max_loss:.2f} exceeds 5% allocation limit (${max_allowed_risk:.2f})."
            )

        # Gate 2: Gross Portfolio Margin Exposure <= 30%
        projected_margin = self.current_margin_used + proposal.max_loss
        margin_utilization = projected_margin / self.account_equity
        if margin_utilization > 0.30:
            return CriticDecision(
                proposal_id=proposal.proposal_id, 
                is_approved=False, 
                rejection_reason=f"GATE 2 FAILED: Projected margin utilization {margin_utilization*100:.2f}% exceeds 30% limit."
            )

        # Gate 5: Net portfolio delta constraint
        if abs(proposal.delta_exposure) > 0.25:
             return CriticDecision(
                proposal_id=proposal.proposal_id, 
                is_approved=False, 
                rejection_reason=f"GATE 5 FAILED: Proposal Delta {proposal.delta_exposure} breaches [-0.25, +0.25] bounds."
            )

        # Evaluate Leg-Specific Gates (3 and 4)
        for i, leg_data in enumerate(leg_market_data):
            bid = leg_data.get("bid", 0.0)
            ask = leg_data.get("ask", 0.0)
            oi = leg_data.get("open_interest", 0)
            
            spread = ask - bid
            
            # Gate 3: Open Interest >= 250
            if oi < 250:
                return CriticDecision(
                    proposal_id=proposal.proposal_id, 
                    is_approved=False, 
                    rejection_reason=f"GATE 3 FAILED: Leg {i} Open Interest ({oi}) < 250."
                )
                
            # Gate 4: Bid-Ask spread <= $0.15
            if spread > 0.15:
                return CriticDecision(
                    proposal_id=proposal.proposal_id, 
                    is_approved=False, 
                    rejection_reason=f"GATE 4 FAILED: Leg {i} Bid-Ask spread (${spread:.2f}) > $0.15."
                )

        # Note: Gates 8 & 9 (Take-Profit & Stop-Loss) are continuous position management gates 
        # evaluated during the active lifecycle of the trade, not at proposal time.
        
        return CriticDecision(
            proposal_id=proposal.proposal_id, 
            is_approved=True, 
            rejection_reason=None
        )
