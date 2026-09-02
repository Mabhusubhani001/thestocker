# ThetaSwarm · Autonomous Options Alpha Desk

Autonomous, fully audited multi-agent options trading desk built on the [Alpaca MCP Server](https://github.com/alpacahq/alpaca-mcp-server) for the **Alpaca AI Trading Agents Hackathon** (Options Alpha Agents track). Features a deterministic mathematical risk engine, a 4-agent dialectic Swarm (CrewAI), full audit trail in SQLite, and a public Streamlit dashboard containing the "Shadow Book" for the jury.

**Public alias:** ThetaSwarm · **Codename:** Options Alpha Desk

### Status — frozen submission branch, 2026-09-04
This branch is the hackathon submission. It is kept as-is so a judge sees exactly what was submitted. It is an experimental paper-trading system built in one week.

### Honest one-liner
We believe a 2-day contest window proves nothing about real AI profitability; therefore, our submission relies on two pillars: (1) A live Streamlit dashboard running against Alpaca Paper Trading to prove our **Fail-Closed Execution Architecture** works end-to-end, and (2) an Episodic Backtest (`RESULTS_LIVE_SWARM.md`) proving our agent's **Predictive Alpha** when forced to trade the 5 highest-impact macro shocks of 2024 using historical news. The system's primary innovation is its complete **Separation of Powers**: the LLM proposes, the Adversarial AI critiques, and a deterministic Python Risk Engine holds final execution authority.

---

## For hackathon judges — start here

| Asset | Link |
| :--- | :--- |
| **Submission Pitch Deck** | [presentation.md](./presentation.md) |
| **Project Narrative & Architecture** | [project_description.md](./project_description.md) |
| **Predictive Alpha Backtest Results** | [RESULTS_LIVE_SWARM.md](./RESULTS_LIVE_SWARM.md) |
| **Full Repo Audit** | [repo_audit_report.md](./repo_audit_report.md) |
| **GitHub Repository** | You are here! |

---

## Quick-start — read-only inspection mode

```bash
git clone https://github.com/YourUsername/thestocker.git
cd thestocker

# Create and activate virtual environment
python -m venv venv
venv\Scripts\Activate.ps1  # or source venv/bin/activate on macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and add your Alpaca Paper Keys and OpenAI-compatible key (e.g. Featherless Qwen)

# Run the Glass-Box Dashboard (Terminal 1)
streamlit run ui/app.py

# Start the Autonomous Swarm Engine (Terminal 2)
python main.py
```

---

## Disclaimer
This project is for hackathon and educational purposes only. It is not financial advice. Live trading involves risk. The system is designed strictly to run against Alpaca Paper Trading environments.

---

## What it does

1. **Polls** public market news and stock prices via the Alpaca API every 3 minutes.
2. **Generates a Thesis**: The Narrative Agent reads the news and predicts the Implied Volatility (IV) regime.
3. **Calculates probabilities**: Extracts real-time option chains and uses Breeden-Litzenberger calculations to find edge.
4. **Builds a Strategy**: The Quant Agent constructs defined-risk multi-leg options structures (e.g. Long Straddles).
5. **Debates**: The Critic Agent attacks the thesis, acting as an adversarial Chief Risk Officer.
6. **Hard Risk Gates**: A deterministic Python `RiskManager` evaluates the trade against 6 non-overridable gates (Margin, Max Loss, Delta limit, Stacked Trades).
7. **Executes**: Approved orders are fired atomically to the **Alpaca MCP Server** via JSON-RPC.
8. **Audits**: Persists every thought, rejection, and fill to a local SQLite `audit.db` and visualizes them on the Streamlit dashboard (The Shadow Book).

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Alpaca API ──> Event Poller ──> Narrative Agent ──> Quant Agent ──> Critic   │
│                                                                              │
│                                                                        ▼     │
│                                           ┌─── No ─── [Shadow Book (UI)]     │
│                                           │                                  │
│                 Risk Engine (6 Gates) ────┤                                  │
│                                           │                                  │
│                                           └── Yes ──> Alpaca MCP Server      │
│                                                                              │
│ Audit DB ─────────────────────────┴─────────> Streamlit Dashboard            │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture

| Layer | Component | Responsibility |
| :--- | :--- | :--- |
| **Config** | `.env` | Environment secrets and Alpaca keys. |
| **Data Ingestion** | `data/event_poller.py` | Polls Alpaca News & Market snapshots. Falls back to mocks safely if market is closed. |
| **Market Data** | `data/alpaca_client.py` | Fetches live options chains, Greeks, and current positions. |
| **Swarm Logic** | `main.py` | Orchestrates the CrewAI Agents (Narrative, Quant, Critic). |
| **Risk Engine** | `risk/risk_manager.py` | Deterministic mathematical guardrails (6 Gates). |
| **Execution** | `execution/mcp_client.py` | Interacts with the `alpaca-mcp-server` over `stdio` using `subprocess`. |
| **Portfolio** | `execution/portfolio_manager.py` | Monitors open positions, manages +20% Take Profit and -50% Stop Loss exits. |
| **Storage** | `storage/audit.py` | SQLite WAL for high-frequency thread-safe logging. |
| **Dashboard** | `ui/app.py` | Glassmorphic Streamlit terminal showing Agent Thoughts and the Shadow Book. |

---

## Strategy & Risk Gates

The AI is explicitly programmed to trade **Defined-Risk Strategies** (e.g., Long Straddles, Credit Spreads, Iron Condors). 

The `RiskManager` sits between the Swarm and the Execution MCP. It enforces **6 Deterministic Gates**:
1. **Gate 1**: Validates correct structure (all legs match).
2. **Gate 2**: Max Absolute Loss (Cap on premium paid or spread width).
3. **Gate 3**: Delta Exposure limit (Ensures portfolio doesn't get wildly directional).
4. **Gate 4**: Live Margin Check (Ensures BP > Initial Margin).
5. **Gate 5**: Banned Tickers (No meme-stock YOLOing).
6. **Gate 6**: No Stacked Trades (Checks live Alpaca positions to prevent duplicate exposure).

*Crucially: The LLM cannot override these gates.*

---

## The Shadow Book

The highlight of the project is the **Shadow Book**, visible on the Streamlit dashboard. 

When the Critic Agent or the Risk Engine rejects a trade, it is logged in the Shadow Book. This allows judges to view the exact math and logic of *why* the AI refused a trade. A true autonomous agent is defined just as much by the trades it doesn't take.

---

## Setup & Submission Readiness

**Prerequisites:** Python 3.10+, an Alpaca Paper Trading Account, and an OpenAI-compatible API key (we recommend Featherless AI for Qwen 2.5 72B).

**Final Checklist before running:**
- [x] `.env` is configured.
- [x] Alpaca Paper account is funded with $100,000.
- [x] Run `python main.py`.
- [x] Run `streamlit run ui/app.py`.

## License
MIT. See `LICENSE`.
