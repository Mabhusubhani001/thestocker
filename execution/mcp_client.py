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
        
        # Track structure in DB for SSE listener to manage
        symbol = proposal_dict.get("symbol", "UNKNOWN")
        strategy_name = proposal_dict.get("strategy_name", "UNKNOWN")
        net_credit = float(proposal_dict.get("net_credit", 0.0))
        self.audit_logger.insert_structure(proposal_id, symbol, strategy_name, net_credit)

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
                            
                            # Track order in DB
                            self.audit_logger.insert_order(proposal_id, tool_args["symbol"], tool_args["side"], int(tool_args["qty"]))
                            
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

    async def close_structure(self, proposal_id: str, orders: list):
        """
        Dynamically closes a structure by firing opposite orders for all its legs.
        Used by the Portfolio Manager for Take Profit / Stop Loss.
        """
        self.audit_logger.log_event("STRUCTURE_CLOSE", f"Closing structure {proposal_id}...")
        
        try:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    for order in orders:
                        try:
                            # Reverse the side
                            close_side = "sell" if order["side"] == "buy" else "buy"
                            
                            tool_args = {
                                "symbol": order["contract_symbol"],
                                "side": close_side,
                                "qty": str(order["qty"]),
                                "type": "market", # Market orders for liquidations to ensure execution
                                "time_in_force": "day"
                            }
                            
                            self.audit_logger.log_event("MCP_TOOL_CALL", f"Closing leg {tool_args['symbol']} with {close_side}")
                            result = await session.call_tool("place_option_order", tool_args)
                            self.audit_logger.log_event("MCP_TOOL_RESULT", f"Result: {result.content}")
                            
                        except Exception as e:
                            self.audit_logger.log_event("MCP_LEG_EXECUTION_ERROR", f"Failed to close leg {order['contract_symbol']}: {str(e)}")
                            
            self.audit_logger.update_structure_status(proposal_id, 'closed')
            
        except Exception as e:
            self.audit_logger.log_event("MCP_CONNECTION_ERROR", f"Failed to reach MCP server during close: {str(e)}")
