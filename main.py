import asyncio
import logging
import os
from data.event_poller import EventPoller
from agents.schemas import VolatilitySignal
from agents.narrative_agent import NarrativeAgent
from agents.quant_agent import QuantAgent
from agents.critic_agent import CriticAgent
from risk.risk_manager import RiskManager
from execution.mcp_client import AlpacaExecutionEngine
from storage.audit_logger import AuditLogger
from crewai import Crew, Process

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ThetaSwarmRunner:
    def __init__(self):
        self.audit_logger = AuditLogger()
        self.execution_engine = AlpacaExecutionEngine(self.audit_logger)
        
        # In a real setup, equity and margin would be fetched live from Alpaca Account API via MCP
        self.risk_manager = RiskManager(
            account_equity=100000.0,
            daily_start_equity=100000.0,
            current_margin_used=0.0,
            active_positions=[]
        )

    async def handle_signal(self, signal: VolatilitySignal):
        """
        Triggered when the EventPoller detects a catalyst.
        Fires up the CrewAI swarm.
        """
        self.audit_logger.log_event("SIGNAL_DETECTED", f"Catalyst found for {signal.symbol}")
        
        # 1. Instantiate Agents
        narrative = NarrativeAgent()
        quant = QuantAgent()
        critic = CriticAgent()
        
        # 2. Create Tasks
        dummy_news = f"Major macroeconomic shift affecting {signal.symbol}. Highly volatile environment expected."
        task1 = narrative.analyze_news_task(dummy_news, signal.symbol)
        
        # Passing mock historical IVs for demonstration
        task2 = quant.design_trade_task(signal.symbol, current_price=500.0, current_iv=0.25, historical_ivs=[0.15, 0.20, 0.30])
        task2.context = [task1] # Quant relies on Narrative's output
        
        task3 = critic.evaluate_trade_task()
        task3.context = [task1, task2] # Critic reviews both
        
        # 3. Assemble Crew
        crew = Crew(
            agents=[narrative.agent, quant.agent, critic.agent],
            tasks=[task1, task2, task3],
            process=Process.sequential,
            verbose=True
        )
        
        # 4. Execute Swarm
        try:
            logger.info("Starting CrewAI Swarm...")
            # Note: This will fail if OPENAI_API_KEY is not in the .env file
            result = await crew.kickoff_async()
            
            self.audit_logger.log_event("SWARM_COMPLETED", "Agents reached a consensus.")
            
            # (In a fully wired production app, we extract task2.output.pydantic and task3.output.pydantic
            # and pass them directly into self.risk_manager.evaluate_proposal and self.execution_engine)
            
        except Exception as e:
            self.audit_logger.log_event("SWARM_ERROR", str(e))
            logger.error(f"Swarm failed: {e}")

async def main():
    runner = ThetaSwarmRunner()
    poller = EventPoller(callback=runner.handle_signal)
    
    logger.info("ThetaSwarm autonomous engine started.")
    await poller.start(["SPY", "QQQ"])

if __name__ == "__main__":
    # Ensure audit directory exists
    os.makedirs("storage", exist_ok=True)
    asyncio.run(main())
