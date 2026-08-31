import asyncio
import logging
import os
from data.event_poller import EventPoller
from agents.schemas import VolatilitySignal
from agents.narrative_agent import NarrativeAgent
from agents.quant_agent import QuantAgent
from agents.critic_agent import CriticAgent
from risk.risk_manager import RiskManager
from data.alpaca_client import AlpacaDataClient
from execution.mcp_client import AlpacaExecutionEngine
from execution.sse_listener import SSEListener
from execution.portfolio_manager import PortfolioManager
from storage.audit_logger import AuditLogger
from crewai import Crew, Process

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ThetaSwarmRunner:
    def __init__(self):
        self.audit_logger = AuditLogger()
        self.execution_engine = AlpacaExecutionEngine(self.audit_logger)
        
        # Fetch live equity and margin from Alpaca Account API
        alpaca_client = AlpacaDataClient()
        account = alpaca_client.get_account()
        
        if account:
            account_equity = float(account.equity)
            daily_start_equity = float(account.last_equity)
            current_margin_used = float(account.initial_margin)
        else:
            # Fallback for local testing if API fails
            account_equity = 100000.0
            daily_start_equity = 100000.0
            current_margin_used = 0.0

        self.risk_manager = RiskManager(
            account_equity=account_equity,
            daily_start_equity=daily_start_equity,
            current_margin_used=current_margin_used,
            active_positions=[]
        )
        
        # Start SSE listener in background
        self.sse_listener = SSEListener()
        self.sse_listener.start()
        
        # Start Portfolio Manager in background
        self.portfolio_manager = PortfolioManager(self.audit_logger, self.execution_engine)
        self.portfolio_manager.start()

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
        # Extract the real headline from the event poller's rationale
        actual_news = signal.rationale.replace("Found macroeconomic catalyst in headline: ", "").strip()
        if not actual_news:
            actual_news = f"Major macroeconomic shift affecting {signal.symbol}. Highly volatile environment expected."
            
        task1 = narrative.analyze_news_task(actual_news, signal.symbol)
        
        # Fetch live price
        alpaca_client = AlpacaDataClient()
        live_price = await alpaca_client.get_current_price(signal.symbol)
        
        # Compute real IV metrics via Newton-Raphson and Historical Returns
        current_iv, historical_ivs = alpaca_client.get_volatility_metrics(signal.symbol, live_price)
        
        task2 = quant.design_trade_task(signal.symbol, current_price=live_price, current_iv=current_iv, historical_ivs=historical_ivs)
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
            quant_output = task2.output.pydantic
            critic_output = task3.output.pydantic
            
            if quant_output and critic_output:
                if critic_output.is_approved:
                    logger.info("Trade approved by Critic. Sending to Risk Manager.")
                    
                    logger.info("Trade approved by Critic. Fetching live option quotes for Risk Manager.")
                    
                    # Fetch live option snapshots for legs to pass Risk Gates 3 and 4
                    contract_symbols = [leg.contract_symbol for leg in quant_output.legs]
                    alpaca_client = AlpacaDataClient()
                    live_leg_data = alpaca_client.get_option_snapshot(contract_symbols)
                    
                    risk_decision = self.risk_manager.evaluate_proposal(quant_output, live_leg_data)
                    
                    if risk_decision.is_approved:
                        logger.info("Trade passed Risk Manager. Executing via MCP.")
                        proposal_dict = quant_output.model_dump()
                        decision_dict = critic_output.model_dump()
                        await self.execution_engine.execute_proposal(proposal_dict, decision_dict, live_leg_data)
                    else:
                        logger.warning(f"Trade rejected by Risk Manager: {risk_decision.rejection_reason}")
                        self.audit_logger.log_event("RISK_MANAGER_REJECTED", f"Trade rejected by Risk Manager: {risk_decision.rejection_reason}")
                else:
                    logger.warning(f"Trade rejected by Critic Agent: {critic_output.rejection_reason}")
            
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
