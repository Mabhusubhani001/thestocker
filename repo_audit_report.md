# ThetaSwarm Repository Audit: Phase 2

After completing a deep dive into the remaining architecture—specifically the `strategies`, `features`, and `agents` directories—I have uncovered a major architectural gap that compromises the integrity of your Risk Engine.

## Critical Flaws Discovered

> [!CAUTION]
> The quantitative logic inside your `strategies` directory completely bypasses the Black-Scholes pricing models and fakes the `max_loss` metrics. If deployed live, the Risk Manager would approve dangerous trades because it is being fed fake loss potentials.

### 1. Fake Net Credit & Max Loss (The `strategies` directory)
* **Files:** `strategies/iron_condor.py`, `strategies/long_straddle.py`, `strategies/bull_put_spread.py`
* **The Mistake:** When the Quant Agent calls the Strategy classes to build a `TradeProposal`, the code accurately fetches the strike prices from Alpaca. However, because it doesn't fetch the real *quotes* (bid/ask) for those strikes, the original developer hardcoded the premium and risk!
  * **Iron Condor (Line 62):** `net_credit = 2.50`
  * **Long Straddle (Line 61):** `net_credit = -5.00`
  * **Bull Put Spread (Line 63):** `net_credit = 1.00`
* **Why this is catastrophic:** The `TradeProposal` passes these fake numbers to the `RiskManager`. Risk Gate 1 (Max Loss <= 5%) uses this fake `max_loss` to evaluate the trade. It is effectively blind.
* **The Fix:** Now that we built `get_option_snapshot()` in `AlpacaDataClient`, we must call it inside the strategy classes, calculate the true credit collected (using real bid/ask spreads), and compute the true `max_loss`.

### 2. Disconnected Greeks Math
* **File:** `features/greeks.py`
* **The Mistake:** You have a beautiful, zero-dependency implementation of the Black-Scholes-Merton model (`calculate_black_scholes`). However, **it is never used anywhere in the codebase.**
* **The Result:** The Strategies currently hardcode their portfolio delta! 
  * `iron_condor.py`: `delta_exposure = 0.0`
  * `bull_put_spread.py`: `delta_exposure = 10.0`
* **Why this is dangerous:** The Risk Manager evaluates Gate 5 (Net Portfolio Delta <= 0.25). If the strategy fakes its delta, the Risk Manager cannot properly balance portfolio exposure.
* **The Fix:** Wire `features/greeks.py` into the `strategies` base class so that every option leg runs through Black-Scholes using the live price and live IV to compute true Delta and Theta.

### 3. Hardcoded Macro Catalyst Triggers
* **File:** `data/event_poller.py`
* **The Mistake:** The poller triggers based on a hardcoded array: `["fed", "fomc", "earnings", "cpi", "rate"]`.
* **The Result:** This is an acceptable shortcut for an MVP, but a true LLM system should pass the raw news headlines directly to the `NarrativeAgent` and let the LLM decide if the news is a catalyst, rather than relying on a basic string-matching heuristic.
* **The Fix:** Have the poller pass all top news headlines to a lightweight routing LLM call, or expand the heuristic dynamically.

## Summary

The Data ingestion, MCP Execution, and Risk Manager are now fully production-ready and using live Alpaca data. 

However, the **Quant Strategies (`strategies/`)** are generating mathematically fraudulent trade proposals. We must fix the `net_credit` and `max_loss` calculations using the new live snapshot function we built earlier.
