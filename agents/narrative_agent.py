import os
from crewai import Agent, Task
from agents.schemas import VolatilitySignal

class NarrativeAgent:
    def __init__(self):
        self.agent = Agent(
            role="Macroeconomic Narrative Analyst",
            goal="Analyze news catalysts and determine the expected direction of implied volatility (expansion or crush).",
            backstory=(
                "You are an elite quantitative researcher who specializes in catalyst-driven volatility. "
                "You do not care about directional price movement. You only care about Implied Volatility. "
                "When a scheduled event (like FOMC or Earnings) passes, IV typically crushes (reverts to mean). "
                "When a surprise macro shock occurs, IV typically expands."
            ),
            verbose=True,
            allow_delegation=False,
            llm=os.environ.get("MODEL_NAME", "gemini/gemini-3.5-flash")
        )

    def analyze_news_task(self, news_text: str, symbol: str) -> Task:
        return Task(
            description=(
                f"Analyze the following news regarding {symbol}:\n\n{news_text}\n\n"
                "Determine if this is a scheduled catalyst that has passed (leading to IV crush) "
                "or a surprise macro shock (leading to IV expansion). "
                "You must provide a confidence score between 0.0 and 1.0 based on the clarity of the text."
            ),
            expected_output="A structured volatility signal indicating 'expansion' or 'crush'.",
            output_pydantic=VolatilitySignal,
            agent=self.agent
        )
