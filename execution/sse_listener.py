import os
import time
import base64
import json
import logging
import threading
import requests
import sseclient
from config.settings import settings
from storage.audit_logger import AuditLogger

logger = logging.getLogger(__name__)

class SSEListener:
    """
    Listens to Alpaca's Server-Sent Events (SSE) trade stream.
    Updates local database state when orders are filled.
    """
    def __init__(self):
        # We use the paper API for Trading API events
        self.url = "https://paper-api.alpaca.markets/v2/events/trades"
        self.db = AuditLogger()
        
        # Prepare Basic Auth header using API Key and Secret
        auth_string = f"{settings.ALPACA_API_KEY}:{settings.ALPACA_SECRET_KEY}"
        b64_auth = base64.b64encode(auth_string.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {b64_auth}",
            "Accept": "text/event-stream"
        }
        
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        """Starts the SSE listener in a background thread."""
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()
            logger.info("SSEListener started in background thread.")

    def stop(self):
        """Stops the listener."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            logger.info("SSEListener stopped.")

    def _listen_loop(self):
        """Main reconnect loop with backoff."""
        backoff = 1
        max_backoff = 60
        
        while not self._stop_event.is_set():
            try:
                logger.info(f"Connecting to SSE stream at {self.url}...")
                response = requests.get(
                    self.url,
                    headers=self.headers,
                    stream=True,
                    timeout=60 # Timeout helps detect dead sockets
                )
                
                if response.status_code != 200:
                    logger.error(f"SSE connection failed with {response.status_code}: {response.text}")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)
                    continue

                client = sseclient.SSEClient(response)
                
                # Connection successful, reset backoff
                backoff = 1
                logger.info("SSE connection established.")
                
                for event in client.events():
                    if self._stop_event.is_set():
                        break
                        
                    # event.event is the stream name, e.g. 'trade_updates'
                    self._process_event(event.data)
                        
            except requests.exceptions.Timeout:
                logger.warning("SSE connection timed out. Reconnecting...")
            except Exception as e:
                logger.error(f"SSE stream error: {e}")
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

    def _process_event(self, raw_data: str):
        """Process incoming trade events idempotently."""
        try:
            payload = json.loads(raw_data)
            event_type = payload.get("event")
            order = payload.get("order", {})
            
            # The OCC symbol is stored in the symbol field for option orders
            contract_symbol = order.get("symbol")
            side = order.get("side")
            status = order.get("status")
            filled_qty = int(order.get("filled_qty") or 0)
            filled_avg_price = float(order.get("filled_avg_price") or 0.0)
            
            logger.info(f"Received trade event: {event_type} for {contract_symbol} ({status})")
            
            if event_type in ["fill", "partial_fill"]:
                # Update the database.
                # In a real system, we'd match on client_order_id.
                # Here we match on contract_symbol and side.
                self.db.update_order_fill(
                    contract_symbol=contract_symbol,
                    side=side,
                    filled_qty=filled_qty,
                    filled_avg_price=filled_avg_price,
                    new_status=status
                )
                self.db.log_event("ORDER_FILLED", f"{side} {filled_qty} of {contract_symbol} at ${filled_avg_price}")
                
        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.error(f"Error processing SSE event: {e}")
