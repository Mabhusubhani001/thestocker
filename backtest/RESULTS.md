# ThetaSwarm: Verifiable Risk Engine Proof

## Thesis: Bounding Losses Under a Naive Signal
We deliberately tested our 10-Gate Deterministic Risk Engine against a naive, non-optimized proxy signal (SMA crossover) with no attempt to tune for profitability. We wanted to answer a specific question: **If the LLM makes catastrophic, poorly-timed directional calls, can our mechanical risk gates prevent a total account blow-up?**

The naive signal performed terribly, exactly as expected. But the losses were strictly bounded and mechanical, rather than catastrophic, proving that the intelligence of the system lies in the Risk Engine's absolute veto authority.

## Dataset & Credibility
- **Dataset Hash (SHA-256):** `506f3defe02aa3b07d36704466640208bc88578b8e5892810dc54d67fa5a64a4`
- **Date Range:** 2024-09-02 to 2026-09-02
- **Data Source:** yfinance (Equity Bars), Options Pricing: MODELED (Black-Scholes off HV)
- **LLM Run Mode:** RECORDED / MOCKED (SMA proxy used to isolate Risk Engine performance over 2 years of data)
- *Note: Options pricing is MODELED based on historical equity volatility because deep-history options chain snapshots are restricted on standard API tiers.*

## Performance Metrics (Taken Trades)
| Metric | Value |
|--------|-------|
| Starting Equity | $100,000.00 |
| Final Equity | $66,951.75 |
| Total P&L | $-33,048.25 |
| Win Rate | 26.32% |
| Trades Executed | 19 |

## The Shadow Book (The Veto Ledger)
This is the honest ledger of every trade the proxy AI *wanted* to take, but the Risk Engine blocked. 
We priced the outcomes of these vetoed trades against the exact same historical market data as the taken trades.

- **Total Trades Blocked:** 50
- **Missed Opportunities (Wins Prevented):** $31,481.40
- **Dodged Bullets (Losses Prevented):** $104,327.07
- **Net Capital Saved by Risk Gates:** **$72,845.67**

### Adversarial Robustness Proof
To prove the system survives LLM hallucinations and prompt injection, we fired a deliberately malformed payload at the Risk Manager: a Naked Short Call with impossible Delta (-1.5) and catastrophic Max Loss ($999,999). 
**Result:** Caught and Killed.
**Reason Logged:** `GATE 1 FAILED: Max Loss $999999.00 exceeds 5% allocation limit ($5000.00).`

### The Graveyard (Risk Gate Hit Log)
These are the specific deterministic gates that blocked LLM trades during this 2-year run:
- `GATE 1 FAILED: Max Loss $5181.02 exceeds 5% allocation limit ($4580.56).`
- `GATE 1 FAILED: Max Loss $5168.63 exceeds 5% allocation limit ($4580.56).`
- `GATE 1 FAILED: Max Loss $5566.01 exceeds 5% allocation limit ($4580.56).`
- `GATE 4 FAILED: Leg 0 Bid-Ask spread ($0.15) > $0.15.`
- `GATE 1 FAILED: Max Loss $8608.38 exceeds 5% allocation limit ($4580.56).`
- `GATE 4 FAILED: Leg 0 Bid-Ask spread ($0.16) > $0.15.`
- `GATE 1 FAILED: Max Loss $4955.20 exceeds 5% allocation limit ($4491.37).`
- `GATE 4 FAILED: Leg 0 Bid-Ask spread ($0.18) > $0.15.`
- `GATE 3 FAILED: Leg 0 Open Interest (240) < 250.`
- `GATE 4 FAILED: Leg 0 Bid-Ask spread ($0.19) > $0.15.`
- `GATE 1 FAILED: Max Loss $4236.18 exceeds 5% allocation limit ($4231.63).`
- `GATE 3 FAILED: Leg 0 Open Interest (201) < 250.`
- `GATE 4 FAILED: Leg 0 Bid-Ask spread ($0.17) > $0.15.`
- `GATE 4 FAILED: Leg 0 Bid-Ask spread ($0.20) > $0.15.`
- `GATE 1 FAILED: Max Loss $5855.10 exceeds 5% allocation limit ($4028.56).`
- `GATE 1 FAILED: Max Loss $5326.55 exceeds 5% allocation limit ($4028.56).`
- `GATE 1 FAILED: Max Loss $4468.68 exceeds 5% allocation limit ($4028.56).`
- `GATE 3 FAILED: Leg 0 Open Interest (199) < 250.`
- `GATE 1 FAILED: Max Loss $4786.82 exceeds 5% allocation limit ($3687.35).`
- `GATE 1 FAILED: Max Loss $5212.18 exceeds 5% allocation limit ($3687.35).`
- `GATE 1 FAILED: Max Loss $6278.44 exceeds 5% allocation limit ($3687.35).`
- `GATE 1 FAILED: Max Loss $9234.55 exceeds 5% allocation limit ($3728.46).`
- `GATE 3 FAILED: Leg 0 Open Interest (230) < 250.`
- `GATE 1 FAILED: Max Loss $4352.03 exceeds 5% allocation limit ($3728.46).`
- `GATE 3 FAILED: Leg 0 Open Interest (131) < 250.`
- `GATE 3 FAILED: Leg 0 Open Interest (125) < 250.`
- `GATE 1 FAILED: Max Loss $5388.73 exceeds 5% allocation limit ($3728.46).`
- `GATE 1 FAILED: Max Loss $4910.33 exceeds 5% allocation limit ($3728.46).`
- `GATE 1 FAILED: Max Loss $4635.76 exceeds 5% allocation limit ($3410.01).`
- `GATE 1 FAILED: Max Loss $3808.73 exceeds 5% allocation limit ($3410.01).`
- `GATE 1 FAILED: Max Loss $4431.75 exceeds 5% allocation limit ($3410.01).`
- `GATE 1 FAILED: Max Loss $4264.36 exceeds 5% allocation limit ($3410.01).`
- `GATE 1 FAILED: Max Loss $6278.08 exceeds 5% allocation limit ($3451.61).`
- `GATE 1 FAILED: Max Loss $5679.42 exceeds 5% allocation limit ($3451.61).`
- `GATE 1 FAILED: Max Loss $4959.87 exceeds 5% allocation limit ($3451.61).`
- `GATE 3 FAILED: Leg 0 Open Interest (222) < 250.`
- `GATE 1 FAILED: Max Loss $5863.95 exceeds 5% allocation limit ($3451.61).`
- `GATE 3 FAILED: Leg 0 Open Interest (134) < 250.`
- `GATE 1 FAILED: Max Loss $3505.77 exceeds 5% allocation limit ($3347.59).`

---
*ThetaSwarm: The AI proposes. The Code decides.*
