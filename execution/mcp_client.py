import asyncio
from typing import Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from storage.audit_logger import AuditLogger

class AlpacaExecutionEngine:
    """
    Connects to the Alpaca MCP Server via JSON-RPC over stdio.
    Executes trades only if they passed the Risk Manager and Critic Agent.
    """
    def __init__(self, audit_logger: AuditLogger):
        # We spawn the official Alpaca MCP server as a local subprocess
        import os
        from config.settings import settings
        
        env = os.environ.copy()
        env["ALPACA_API_KEY"] = settings.ALPACA_API_KEY
        env["ALPACA_SECRET_KEY"] = settings.ALPACA_SECRET_KEY
        env["ALPACA_PAPER_TRADE"] = str(settings.ALPACA_PAPER).lower()

        self.server_params = StdioServerParameters(
            command="uvx",
            args=["alpaca-mcp-server"],
            env=env
        )
        self.audit_logger = audit_logger

    async def execute_proposal(self, proposal_dict: Dict[str, Any], decision_dict: Dict[str, Any], live_leg_data: list = None):
        """
        Evaluates the Critic's decision. If approved, fires JSON-RPC commands to MCP.
        """
        proposal_id = proposal_dict.get('proposal_id', 'UNKNOWN')
        
        # FINAL SAFETY CHECK
        if not decision_dict.get("is_approved", False):
            self.audit_logger.log_event(
                "TRADE_REJECTED", 
                f"Proposal {proposal_id} blocked: {decision_dict.get('rejection_reason')}"
            )
            return
            
        self.audit_logger.log_event("TRADE_APPROVED", f"Proposal {proposal_id} approved. Firing JSON-RPC over stdio...")
        
        try:
            # Connect via stdio pipes
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    for i, leg in enumerate(proposal_dict.get("legs", [])):
                        try:
                            # Calculate Limit Price based on live quotes to avoid slippage
                            # Use Ask for buying, Bid for selling
                            limit_price = 1.00
                            if live_leg_data and i < len(live_leg_data):
                                ask = live_leg_data[i].get("ask", 1.00)
                                bid = live_leg_data[i].get("bid", 1.00)
                                limit_price = ask if leg["side"] == "buy" else bid
                                
                            # If quote is 0.0 (market closed/illiquid), mock it safely for paper trading
                            if limit_price <= 0:
                                limit_price = 1.00

                            tool_args = {
                                "symbol": leg["contract_symbol"],
                                "side": leg["side"],
                                "qty": str(leg["ratio"]),
                                "type": "limit",
                                "time_in_force": "day",
                                "limit_price": str(round(limit_price, 2))
                            }
                            
                            self.audit_logger.log_event("MCP_TOOL_CALL", f"Calling place_option_order for {tool_args['symbol']}")
                            
                            # Execute the trade via MCP Server
                            result = await session.call_tool("place_option_order", tool_args)
                            
                            # Log the raw JSON-RPC response from Alpaca
                            self.audit_logger.log_event("MCP_TOOL_RESULT", f"Result: {result.content}")
                        except Exception as e:
                            self.audit_logger.log_event("MCP_LEG_EXECUTION_ERROR", f"Failed on leg {leg.get('contract_symbol')}: {str(e)}")
                            # Break out to avoid partial multi-leg fills in a real environment
                            break
                            
        except Exception as e:
            self.audit_logger.log_event("MCP_CONNECTION_ERROR", f"Failed to reach MCP server: {str(e)}")
