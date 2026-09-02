# Slide 1: Title Slide
**Title:** ThetaSwarm: Autonomous Options Alpha Desk
**Subtitle:** The AI hedge fund that separates intelligence from execution. 4 Specialized Agents. Mathematical Guardrails. Zero Human Emotion.
**Visual Idea:** A sleek, dark-mode futuristic trading terminal background with the Alpaca and CrewAI logos.

---

# Slide 2: The Problem
**Title:** Why Most AI Trading Agents Fail
**Subtitle:** Giving an LLM the keys to your brokerage account is a recipe for disaster.

- 🤯 **The "Black Box" Problem:** Most AI bots invent trades based on hallucinations without showing their math.
- 🎰 **Zero Risk Discipline:** An LLM might be great at reading news, but it is terrible at managing portfolio exposure or understanding options pricing.
- 📉 **The Retail Disadvantage:** Retail traders lose money because of emotional decision-making and delayed execution during macro shocks. 

**The Solution?** You don't let the AI trade. You let the AI *propose*, and you let deterministic code *decide*.

---

# Slide 3: Our Solution & Core Thesis
**Title:** The "Fail-Closed" Architecture
**Subtitle:** Intelligence is Autonomous. Execution is Governed.

**ThetaSwarm** is an autonomous options-trading agent built for the Alpaca AI Trading Agents Hackathon. It is designed around one strict principle: **Separation of Powers.**
- **The AI Swarm** (powered by Qwen 2.5 72B) continuously reads market news, calculates Breeden-Litzenberger probabilities, and proposes options strategies.
- **The Adversarial Critic** red-teams the trade, looking for any excuse to veto it.
- **The Hard-Coded Risk Engine** applies 6 deterministic mathematical gates. If a trade fails even one, it is killed instantly. 

---

# Slide 4: The Agent Workflow
**Title:** From Market Signal to Live Alpaca Execution
**Visual Idea:** A flow chart moving from left to right.

1. 📰 **Market Data (Poller):** Ingests live news and Alpaca market snapshots every 3 minutes.
2. 🧠 **Narrative Agent:** Reads the news and predicts Implied Volatility (Expansion vs. Crush).
3. 📐 **Quant Agent:** Fetches live option chains and structures a defined-risk multi-leg trade (e.g., Long Straddle).
4. 🛑 **The Critic & Risk Manager:** The Critic attacks the thesis. The Python Risk Manager checks buying power and max loss limits.
5. ⚡ **Alpaca MCP Execution:** If approved, atomic multi-leg orders are fired directly to the Alpaca Paper Trading exchange via the Model Context Protocol (MCP).

---

# Slide 5: Performance & The Shadow Book
**Title:** A Trading Agent You Can Actually Audit
**Subtitle:** Good trading is about the trades you *don't* take.

- 📊 **Predictive Alpha Backtest:** We didn't just build a bot; we proved it works. Against the 5 largest macro shocks of 2024, our Live Swarm Episodic Backtester structured options trades that captured the volatility, turning a profit when the rest of the market panicked. 
- 🛡️ **The Shadow Book:** Our live Streamlit dashboard features "The Shadow Book," an append-only cryptographic ledger of every trade the AI *refused* to take. 
- **Example:** On Day 1, the Quant Agent proposed a Bull Put Spread, but the Critic Agent rejected it because the IV thesis was misaligned, saving capital from a mathematically poor setup. 

---

# Slide 6: The Tech Stack
**Title:** Built on Modern, Institutional-Grade Infrastructure
**Visual Idea:** Grid of logos (Python, CrewAI, Alpaca, Streamlit).

- **Backend:** Python, SQLite (for audit logging), CrewAI (for agent orchestration).
- **AI Brain:** Qwen-2.5-72B-Instruct running via Featherless AI for sub-second, model-agnostic reasoning.
- **Broker & Data:** Alpaca Markets API (for live chains) and Alpaca MCP Server for secure, locked-down order execution.
- **Frontend:** A Bloomberg-style, glassmorphic Streamlit web terminal showing live Agent Thoughts, Portfolio Greeks, and active executions. 

---

# Slide 7: Conclusion
**Title:** Ready for Judge Verification
**Subtitle:** Transparent, Reproducible, Risk-Aware.

**Track:** Options Alpha Agents
**Live Proof:** 
- End-to-end execution verified on Alpaca Paper Servers.
- Real multi-leg options contracts (Straddles, Credit Spreads) generated autonomously.
- No fake fills. No hidden curve-fitting. 

**Takeaway:** We didn't just build a trading bot. We built the fortress around it. 

**GitHub:** github.com/YourUsername/thestocker
**Alpaca Account:** [Insert Your PA... Account ID Here]
