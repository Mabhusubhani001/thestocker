import time
import logging
import asyncio
import threading
from datetime import datetime
from zoneinfo import ZoneInfo
from storage.audit_logger import AuditLogger
from data.alpaca_client import AlpacaDataClient
from execution.mcp_client import AlpacaExecutionEngine
from config.settings import settings

def trigger_autopsy(proposal_id):
    try:
        from agents.autopsy_agent import run_autopsy
        run_autopsy(proposal_id)
    except Exception as e:
        logger.error(f"Failed to run autopsy for {proposal_id}: {e}")

logger = logging.getLogger(__name__)

class PortfolioManager:
    """
    Continuous background loop that monitors active options structures for 
    Take Profit (Gate 8) and Stop Loss (Gate 9) conditions.
    """
    def __init__(self, audit_logger: AuditLogger, execution_engine: AlpacaExecutionEngine):
        self.db = audit_logger
        self.execution_engine = execution_engine
        self.data_client = AlpacaDataClient()
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
            self._thread.start()
            logger.info("PortfolioManager started in background thread.")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            logger.info("PortfolioManager stopped.")

    def _run_async_loop(self):
        # We need an event loop for the async execution engine calls
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._monitor_loop())
        except Exception as e:
            logger.error(f"PortfolioManager loop crashed: {e}")
        finally:
            loop.close()

    async def _monitor_loop(self):
        while not self._stop_event.is_set():
            try:
                # Run the check every 60 seconds
                await self._check_positions()
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"PortfolioManager error: {e}")
                await asyncio.sleep(10)

    async def _check_positions(self):
        structures = self.db.get_active_structures()
        
        # Check Gate 10 (Thursday EOD Liquidation) time
        tz = ZoneInfo(settings.LIQUIDATION_TIMEZONE)
        now_et = datetime.now(tz)
        is_liquidation_time = False
        if now_et.weekday() == settings.LIQUIDATION_DAY_OF_WEEK:
            if now_et.hour > settings.LIQUIDATION_HOUR or \
               (now_et.hour == settings.LIQUIDATION_HOUR and now_et.minute >= settings.LIQUIDATION_MINUTE):
                is_liquidation_time = True
        
        # 1. Fetch live open positions from Alpaca for Reconciliation
        positions_fetched = False
        try:
            positions = self.data_client.trading_client.get_all_positions()
            open_symbols = {p.symbol for p in positions}
            positions_fetched = True
        except Exception as e:
            logger.error(f"Error fetching positions for reconciliation: {e}")
            open_symbols = set()
            
        for structure in structures:
            proposal_id = structure["proposal_id"]
            initial_credit = structure["net_credit_target"]
            strategy_name = structure["strategy_name"]
            
            orders = self.db.get_structure_orders(proposal_id)
            if not orders:
                continue
                
            # If any orders are still 'new', the structure isn't fully filled yet. Wait.
            if any(o["status"] == 'new' for o in orders):
                continue

            contract_symbols = [o["contract_symbol"] for o in orders]
            
            # 2. Reconciliation Check:
            # If the structure is active in our DB, but ANY of its contract symbols are missing from Alpaca's open positions,
            # it means the user manually closed part or all of it on the UI. The AI should relinquish control.
            if positions_fetched and any(sym not in open_symbols for sym in contract_symbols):
                logger.info(f"Reconciliation: Structure {proposal_id} was manually modified by user. Relinquishing AI control.")
                self.db.update_structure_status(proposal_id, 'closed')
                for o in orders:
                    self.db.update_order_fill(o["contract_symbol"], o["side"], o["qty"], 0.0, 'closed')
                continue
                
            # Gate 10: Active Liquidation
            if is_liquidation_time:
                logger.warning(f"[GATE 10: EOD LIQUIDATION] Liquidating {proposal_id} before weekend.")
                await self.execution_engine.close_structure(proposal_id, orders)
                threading.Thread(target=trigger_autopsy, args=(proposal_id,)).start()
                continue
            
            # Fetch live snapshots
            snapshots = self.data_client.get_option_snapshot(contract_symbols)
            
            valid_quotes = True
            current_mtm = 0.0
            for i, order in enumerate(orders):
                quote = snapshots[i]
                ask = quote.get("ask", 0.0)
                bid = quote.get("bid", 0.0)
                qty = order["qty"]
                
                if ask <= 0.0 or bid <= 0.0:
                    valid_quotes = False
                    break
                
                # To close a short position, we buy at the ask. 
                # To close a long position, we sell at the bid.
                # So the MTM value of the structure is the cost to close it.
                if order["side"] == "sell":
                    current_mtm -= (ask * qty)
                else:
                    current_mtm += (bid * qty)
                    
            if not valid_quotes:
                logger.info(f"Skipping MTM evaluation for {proposal_id} due to zero-quotes (illiquid/halted).")
                continue
                    
            # For a credit strategy (Iron Condor, Credit Spread):
            # We collected `initial_credit`. 
            # To close it, we pay `current_mtm` (which will be a negative number because buying back costs money).
            # The net profit is `initial_credit + current_mtm`.
            # Example: Collected $2.50. current_mtm = -1.25. Profit = 1.25 (50% profit!).
            
            # Branch logic based on whether it is a Credit or Debit Strategy
            if initial_credit > 0:
                # Credit Strategy (e.g. Iron Condor, Credit Spread)
                # Stop Loss (Gate 9): If it costs 2x the credit to close
                if current_mtm <= (initial_credit * -2.0):
                    logger.warning(f"[GATE 9: STOP LOSS] {proposal_id} MTM is {current_mtm}. Initial credit was {initial_credit}. Liquidating.")
                    await self.execution_engine.close_structure(proposal_id, orders)
                    threading.Thread(target=trigger_autopsy, args=(proposal_id,)).start()
                    
                # Take Profit (Gate 8): If it costs 80% of the credit to close (we keep 20% profit)
                elif current_mtm >= (initial_credit * -0.8):
                    logger.info(f"[GATE 8: TAKE PROFIT] {proposal_id} MTM is {current_mtm}. Initial credit was {initial_credit}. Taking profit.")
                    await self.execution_engine.close_structure(proposal_id, orders)
                    threading.Thread(target=trigger_autopsy, args=(proposal_id,)).start()
            else:
                # Debit Strategy (e.g. Long Straddle)
                initial_cost = abs(initial_credit)
                # Stop Loss (Gate 9): If the value of the long options drops by 50%
                if current_mtm <= (initial_cost * 0.5):
                    logger.warning(f"[GATE 9: STOP LOSS] {proposal_id} MTM is {current_mtm}. Initial cost was {initial_cost}. Liquidating.")
                    await self.execution_engine.close_structure(proposal_id, orders)
                    threading.Thread(target=trigger_autopsy, args=(proposal_id,)).start()
                    
                # Take Profit (Gate 8): If the value of the long options increases by 20%
                elif current_mtm >= (initial_cost * 1.2):
                    logger.info(f"[GATE 8: TAKE PROFIT] {proposal_id} MTM is {current_mtm}. Initial cost was {initial_cost}. Taking profit.")
                    await self.execution_engine.close_structure(proposal_id, orders)
                    threading.Thread(target=trigger_autopsy, args=(proposal_id,)).start()
