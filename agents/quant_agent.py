import os
from crewai import Agent, Task
from crewai.tools import tool
from agents.schemas import TradeProposal
from strategies.iron_condor import IronCondorStrategy
from strategies.long_straddle import LongStraddleStrategy
from strategies.bull_put_spread import BullPutSpreadStrategy
from features.regime import calculate_iv_rank

@tool("Construct Iron Condor")
def construct_iron_condor(symbol: str, current_price: float, iv_rank: float) -> str:
    """Constructs a delta-neutral Iron Condor strategy to capture IV crush."""
    strategy = IronCondorStrategy(symbol, current_price, iv_rank)
    proposal = strategy.construct_proposal()
    return proposal.model_dump_json()

@tool("Construct Long Straddle")
def construct_long_straddle(symbol: str, current_price: float, iv_rank: float) -> str:
    """Constructs a Long Straddle strategy to capture IV expansion and large price movements."""
    strategy = LongStraddleStrategy(symbol, current_price, iv_rank)
    proposal = strategy.construct_proposal()
    return proposal.model_dump_json()

@tool("Construct Bull Put Spread")
def construct_bull_put_spread(symbol: str, current_price: float, iv_rank: float) -> str:
    """Constructs a Bull Put Spread strategy to capture a bullish move with defined risk."""
    strategy = BullPutSpreadStrategy(symbol, current_price, iv_rank)
    proposal = strategy.construct_proposal()
    return proposal.model_dump_json()

class QuantAgent:
    def __init__(self):
        self.agent = Agent(
            role="Quantitative Options Strategist",
            goal="Design optimal defined-risk options structures based on the narrative catalyst and IV Rank.",
            backstory=(
                "You are a strict, mathematically driven quant. You do not trade naked options. "
                "If the Narrative Agent predicts IV Crush (implied_volatility_bias='crush'), you construct an Iron Condor to sell premium. "
                "If the Narrative Agent predicts IV Expansion (implied_volatility_bias='expansion'), you construct a Long Straddle to buy premium. "
                "If the Narrative Agent predicts Neutral but bullish bias, you construct a Bull Put Spread. "
                "You rely strictly on your tools to generate the exact strikes and proposals. You never guess strikes yourself. "
                "You must respect the market-implied risk-neutral probabilities (derived via Breeden-Litzenberger P(S>K) = -dC/dK) provided to you. "
                "Always aim to structure trades where the short strikes have a mathematically derived probability of <20% of being breached."
            ),
            verbose=True,
            tools=[construct_iron_condor, construct_long_straddle, construct_bull_put_spread],
            allow_delegation=False,
            llm=os.environ.get("MODEL_NAME", "openai/Qwen/Qwen2.5-7B-Instruct")
        )
        
    def design_trade_task(self, symbol: str, current_price: float, current_iv: float, historical_ivs: list) -> Task:
        iv_rank = calculate_iv_rank(current_iv, historical_ivs)
        
        # Calculate Breeden-Litzenberger risk-neutral probabilities for context
        from data.alpaca_client import AlpacaDataClient
        alpaca_client = AlpacaDataClient()
        prob_context = alpaca_client.get_breeden_litzenberger_probabilities(symbol, current_price)
        
        return Task(
            description=(
                f"The underlying {symbol} is trading at ${current_price}. The IV Rank is {iv_rank:.2f}%.\n"
                f"{prob_context}\n"
                "Based on the Narrative Agent's VolatilitySignal (passed as context) and the Breeden-Litzenberger probabilities, construct the appropriate options strategy using your tools."
            ),
            expected_output="A fully populated TradeProposal containing the exact option legs.",
            output_pydantic=TradeProposal,
            agent=self.agent
        )

