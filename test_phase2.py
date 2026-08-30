import asyncio
from data.event_poller import EventPoller
from agents.schemas import VolatilitySignal

def handle_signal(signal: VolatilitySignal):
    print(f"\n🚀 SIGNAL RECEIVED: {signal.symbol} -> {signal.catalyst_type}")
    print(f"Rationale: {signal.rationale}\n")

async def main():
    poller = EventPoller(callback=handle_signal)
    
    # Run the poller in the background
    task = asyncio.create_task(poller.start(["SPY"]))
    
    # Let it run one cycle, then stop
    await asyncio.sleep(2)
    poller.stop()
    await task

asyncio.run(main())
