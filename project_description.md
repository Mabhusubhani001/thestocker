# ThetaSwarm: The Neuro-Symbolic Options Desk

**Created for the Alpaca AI Trading Agents Hackathon**

## The Problem
Most AI trading agents hand a Large Language Model the keys to a brokerage account and hope for the best. They allow the LLM to generate strikes, sizes, and risk limits based on "vibes" rather than mathematics. Over a long enough time horizon, these agents blow up accounts. LLMs are excellent at reading market sentiment and narratives, but they are notoriously terrible at quantitative math, probability theory, and risk discipline.

## Our Solution: The AI in a Straitjacket
**ThetaSwarm** is an autonomous, neuro-symbolic options trading desk. We built it on a single uncompromising principle: **The AI proposes, but deterministic code decides.** 

We separated intelligence from execution. We use a multi-agent LLM swarm strictly for market analysis and directional thesis generation. However, the AI has absolutely zero authority to size a position, pick a strike price, or route an order. Every AI proposal is fed into a 100% deterministic Python risk engine that calculates live Black-Scholes Greeks, applies strict portfolio guardrails, and enforces mathematical discipline before Alpaca ever sees an order ticket.

## How It Works (The Architecture)

### 1. The Autonomous Swarm (The Brains)
When a macroeconomic catalyst hits the wire (e.g., FOMC rate decisions, CPI data), the Event Poller wakes up a CrewAI Swarm.
*   **The Narrative Analyst:** Reads the news and determines if this is a scheduled event (leading to IV crush) or a macro shock (leading to IV expansion).
*   **The Quant Strategist:** Takes the narrative and proposes an options strategy (e.g., Iron Condor, Debit Spread).
*   **The Critic:** Red-teams the proposal. If the thesis is weak, the Critic kills the trade on the spot.

### 2. The 10-Gate Risk Engine (The Muscle)
If the Swarm reaches a consensus, the trade is handed to the Risk Engine. The LLM is now locked out of the loop. The Risk Engine connects to Alpaca's Market Data API and runs the proposal through 10 deterministic gates in milliseconds:
1.  **Slippage & Liquidity:** Rejects illiquid contracts and calculates bid/ask spread penalty.
2.  **Newton-Raphson IV:** Calculates live Implied Volatility against historical Realized Volatility.
3.  **Delta/Gamma Bounding:** Ensures the portfolio does not become over-leveraged to directional risk.
4.  **Max Loss Cap:** Enforces a strict 5% equity risk limit per trade.
5.  **Margin Utilization:** Hard cap at 30% total account margin.
6.  **Concentration:** Max 1 structure per underlying ticker.
7.  ...and 4 other stringent safety checks.

If a trade fails *any* gate, it is vetoed. The AI cannot override this.

### 3. The Immutable Ledger & Shadow Book
Transparency is paramount. Every single decision—from the Swarm's internal debates to the Risk Engine's vetoes—is recorded in an append-only SQLite database. 
Our live Streamlit dashboard features **"The Shadow Book,"** which tracks every trade the AI *wanted* to take but the Risk Engine *blocked*. By pricing these blocked trades against live market data, we mathematically prove how much capital our deterministic gates saved the portfolio.

### 4. Execution & Autopsies
Approved trades are natively routed through Alpaca's Model Context Protocol (MCP) and Trading API as atomic, multi-leg (`OrderClass.MLEG`) orders. Once closed, an Autopsy Agent analyzes the P&L and writes a markdown post-mortem to the Ledger.

## The Tech Stack
*   **Broker & Market Data:** Alpaca Trading API, Alpaca Market Data API, Alpaca MCP Server.
*   **Intelligence:** CrewAI, Featherless AI (Pending Integration).
*   **Backend & Risk:** Python 3.12, SQLite (WAL mode), Asyncio/Threading.
*   **Frontend:** Streamlit 1.37 (utilizing `@st.fragment` for zero-flicker, 2-second real-time telemetry updates).

## Conclusion
ThetaSwarm doesn't just automate trading; it automates institutional risk management. We don't brag about how many trades our AI takes. We brag about the ones it refuses.
