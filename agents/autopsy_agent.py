import logging
import sqlite3
from crewai import Agent, Task, Crew, Process
from pydantic import BaseModel, Field
from data.alpaca_client import AlpacaDataClient

logger = logging.getLogger(__name__)

class AutopsyReport(BaseModel):
    report_markdown: str = Field(description="The full markdown post-mortem report.")

def run_autopsy(proposal_id: str):
    logger.info(f"Starting Autopsy Agent for {proposal_id}")
    db_path = "storage/audit.db"
    
    # Fetch structure and order data
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        structure = conn.execute("SELECT * FROM structures WHERE proposal_id = ?", (proposal_id,)).fetchone()
        if not structure:
            logger.error(f"Autopsy failed: Structure {proposal_id} not found.")
            return
            
        orders = conn.execute("SELECT * FROM orders WHERE proposal_id = ?", (proposal_id,)).fetchall()
        
    symbol = structure["symbol"]
    strategy = structure["strategy_name"]
    initial_credit = structure["net_credit_target"]
    
    # Calculate final P&L
    total_credit = 0.0
    total_debit = 0.0
    for o in orders:
        if o["side"] == "sell":
            total_credit += (o["filled_avg_price"] * o["qty"])
        else:
            total_debit += (o["filled_avg_price"] * o["qty"])
            
    # For a trade to be closed, the orders table has both open and close legs.
    # Actually, our PortfolioManager just calls Alpaca to close the structure, and the SSE listener updates the orders table.
    # Let's just calculate the net cashflow of all orders for this proposal.
    net_cashflow = total_credit - total_debit
    
    # Fetch current news for context on what happened
    import asyncio
    alpaca_client = AlpacaDataClient()
    try:
        # Check if an event loop is already running
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If running in a thread with a loop, this shouldn't happen based on portfolio_manager's threading,
            # but to be safe, we can use a new loop if needed or just use run_until_complete
            news = loop.run_until_complete(alpaca_client.get_latest_news([symbol], limit=3))
        else:
            news = loop.run_until_complete(alpaca_client.get_latest_news([symbol], limit=3))
    except RuntimeError:
        news = asyncio.run(alpaca_client.get_latest_news([symbol], limit=3))
        
    news_headlines = [n.get("headline", "") for n in news]
    
    trade_summary = f"""
    Symbol: {symbol}
    Strategy: {strategy}
    Initial Credit Target: {initial_credit}
    Total Net Cashflow (P&L): {net_cashflow:.2f}
    """
    
    import os
    autopsy_agent = Agent(
        role="Quantitative Post-Mortem Analyst",
        goal="Analyze closed options trades and generate insightful post-mortem reports explaining why they won or lost.",
        backstory="You are an expert options trader and quantitative researcher. Your job is to analyze the final P&L of a trade against recent news events, providing clear, actionable insights into what the market did and why the trade resulted in profit or loss.",
        verbose=True,
        llm=os.environ.get("MODEL_NAME", "openai/Qwen/Qwen2.5-7B-Instruct")
    )
    
    autopsy_task = Task(
        description=f"""
        Analyze the following closed trade and recent market news to write a post-mortem report.
        
        Trade Summary:
        {trade_summary}
        
        Recent News on {symbol}:
        {news_headlines}
        
        Write a concise, professional markdown report (max 300 words). 
        Include:
        1. A summary of the trade (Win/Loss)
        2. A hypothesis on what drove the market (based on the news)
        3. A conclusion on whether the risk gates acted correctly.
        """,
        expected_output="A professional markdown post-mortem report.",
        agent=autopsy_agent,
        output_pydantic=AutopsyReport
    )
    
    crew = Crew(
        agents=[autopsy_agent],
        tasks=[autopsy_task],
        process=Process.sequential,
        verbose=True
    )
    
    result = crew.kickoff()
    
    if hasattr(result, 'pydantic') and result.pydantic:
        report = result.pydantic.report_markdown
    else:
        report = str(result)
        
    # Save to database
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO trade_autopsies (proposal_id, report_markdown, timestamp) VALUES (?, ?, datetime('now'))",
            (proposal_id, report)
        )
        
    logger.info(f"Autopsy completed for {proposal_id}")
