import os
from crewai import Agent, Task
from crewai.tools import tool
from agents.schemas import TradeProposal
from strategies.iron_condor import IronCondorStrategy
from features.regime import calculate_iv_rank

@tool("Construct Iron Condor")
def construct_iron_condor(symbol: str, current_price: float, iv_rank: float) -> str:
    """Constructs a delta-neutral Iron Condor strategy to capture IV crush."""
    strategy = IronCondorStrategy(symbol, current_price, iv_rank)
    proposal = strategy.construct_proposal()
    return proposal.model_dump_json()

class QuantAgent:
    def __init__(self):
        self.agent = Agent(
            role="Quantitative Options Strategist",
            goal="Design optimal defined-risk options structures based on the narrative catalyst and IV Rank.",
            backstory=(
                "You are a strict, mathematically driven quant. You do not trade naked options. "
                "If the Narrative Agent predicts IV Crush, you construct an Iron Condor to sell premium. "
                "You rely strictly on the 'Construct Iron Condor' tool to generate the exact strikes. "
                "You never guess strikes yourself."
            ),
            verbose=True,
            tools=[construct_iron_condor],
            allow_delegation=False,
            llm=os.environ.get("MODEL_NAME", "gemini/gemini-3.5-flash")
        )
        
    def design_trade_task(self, symbol: str, current_price: float, current_iv: float, historical_ivs: list) -> Task:
        iv_rank = calculate_iv_rank(current_iv, historical_ivs)
        return Task(
            description=(
                f"The underlying {symbol} is trading at ${current_price}. The IV Rank is {iv_rank:.2f}%.\n"
                "Based on the Narrative Agent's VolatilitySignal (passed as context), construct the appropriate options strategy using your tools."
            ),
            expected_output="A fully populated TradeProposal containing the exact option legs.",
            output_pydantic=TradeProposal,
            agent=self.agent
        )
