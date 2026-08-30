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
        self.server_params = StdioServerParameters(
            command="uvx",
            args=["alpaca-mcp-server"],
            env=None # Inherits from process env, which loads from .env
        )
        self.audit_logger = audit_logger

    async def execute_proposal(self, proposal_dict: Dict[str, Any], decision_dict: Dict[str, Any]):
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
                    
                    for leg in proposal_dict.get("legs", []):
                        # Map our OptionsLeg schema to the Alpaca MCP 'place_option_order' schema
                        tool_args = {
                            "symbol": leg["contract_symbol"],
                            "side": leg["side"],
                            "qty": str(leg["ratio"]),
                            "type": "market",
                            "time_in_force": "day"
                        }
                        
                        self.audit_logger.log_event("MCP_TOOL_CALL", f"Calling place_option_order: {tool_args}")
                        
                        # Execute the trade via MCP Server
                        result = await session.call_tool("place_option_order", tool_args)
                        
                        # Log the raw JSON-RPC response from Alpaca
                        self.audit_logger.log_event("MCP_TOOL_RESULT", f"Result: {result.content}")
                        
        except Exception as e:
            self.audit_logger.log_event("MCP_CONNECTION_ERROR", f"Failed to reach MCP server: {str(e)}")
