import os
from crewai import Agent, Task
from agents.schemas import CriticDecision

class CriticAgent:
    def __init__(self):
        self.agent = Agent(
            role="Adversarial Chief Risk Officer",
            goal="Cross-examine the Quant Agent's trade proposal against the Narrative Agent's thesis to find any logical inconsistencies.",
            backstory=(
                "You are a deeply skeptical and adversarial risk manager. "
                "Your job is to poke holes in the trade. "
                "If the Narrative Agent says IV is expanding, but the Quant Agent sells an Iron Condor (which is short Vega / needs IV to drop), "
                "you must REJECT the trade immediately. You only approve trades where the strategy perfectly aligns with the volatility thesis."
            ),
            verbose=True,
            allow_delegation=False,
            llm=os.environ.get("MODEL_NAME", "openai/Qwen/Qwen2.5-7B-Instruct")
        )

    def evaluate_trade_task(self) -> Task:
        return Task(
            description=(
                "Review the outputs from both the Narrative Agent (VolatilitySignal) and the Quant Agent (TradeProposal).\n"
                "Check for logical alignment: Does the strategy profit from the expected volatility direction? "
                "Are the strikes logical? "
                "Output your final decision."
            ),
            expected_output="A structured CriticDecision indicating your strict approval status (True/False) and a detailed rationale.",
            output_pydantic=CriticDecision,
            agent=self.agent
        )
