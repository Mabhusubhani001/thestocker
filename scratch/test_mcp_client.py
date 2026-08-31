import asyncio
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from storage.audit_logger import AuditLogger
from execution.mcp_client import AlpacaExecutionEngine

async def main():
    logger = AuditLogger()
    engine = AlpacaExecutionEngine(logger)
    
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    
    print(f"Testing MCP Server with args: {engine.server_params.args}")
    try:
        async with stdio_client(engine.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                print("Initializing session...")
                await session.initialize()
                print("Initialized successfully!")
                tools = await session.list_tools()
                for t in tools.tools:
                    print(f"Tool: {t.name}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
