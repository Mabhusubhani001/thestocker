import streamlit as st
import sqlite3
import pandas as pd
import os
import sys
from pathlib import Path

# Add project root to sys.path to allow importing config and data modules
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from alpaca.trading.client import TradingClient
from data.alpaca_client import AlpacaDataClient

st.set_page_config(page_title="TheStocker | AI Terminal", layout="wide", initial_sidebar_state="expanded")

# Premium CSS Injection
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Base Theme */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0B0F19; /* Deep slate background */
        color: #E2E8F0;
    }
    
    /* Premium Metric Cards with Glassmorphism */
    div[data-testid="metric-container"] {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 1.25rem;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2), 0 2px 4px -1px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        backdrop-filter: blur(10px);
    }
    
    div[data-testid="metric-container"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2);
        border-color: rgba(255, 255, 255, 0.2);
    }
    
    /* Typography */
    h1, h2, h3 {
        color: #F8FAFC !important;
        font-weight: 600 !important;
        letter-spacing: -0.025em;
    }
    
    h1 {
        background: -webkit-linear-gradient(45deg, #38BDF8, #34D399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: rgba(30, 41, 59, 0.5);
        border-radius: 0.375rem;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Dataframe wrapper styling */
    div[data-testid="stDataFrame"] {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 0.5rem;
        padding: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ TheStocker")
st.markdown("### A fully autonomous team of AI quantitative traders. They read the news, run the math, and execute trades while strictly managing risk—all in real-time.")

st.sidebar.header("System Status")
st.sidebar.success("🟢 AI News Radar: ACTIVE")
st.sidebar.success("🟢 Immutable Ledger: ACTIVE")
st.sidebar.info("🤖 AI Trading Swarm: STANDBY")

# Risk Limits UI
st.sidebar.markdown("---")
st.sidebar.subheader("Safety Guardrails (Active)")
st.sidebar.checkbox("Maximum Risk Limit: 5%", value=True, disabled=True)
st.sidebar.checkbox("Margin Usage Cap: 30%", value=True, disabled=True)
st.sidebar.checkbox("Weekend Safety (Liquidate Thursdays)", value=True, disabled=True)

db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "audit.db")

def get_audit_logs():
    try:
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql_query("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 50", conn)
    except Exception:
        return pd.DataFrame()

def get_alpaca_account():
    if not settings.ALPACA_API_KEY:
        return None
    try:
        client = TradingClient(settings.ALPACA_API_KEY, settings.ALPACA_SECRET_KEY, paper=settings.ALPACA_PAPER)
        return client.get_account()
    except Exception as e:
        st.error(f"Failed to fetch Alpaca account: {e}")
        return None

def get_shadow_book():
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM rejected_proposals ORDER BY timestamp DESC")
            proposals = [dict(row) for row in cursor.fetchall()]
            for p in proposals:
                cursor = conn.execute("SELECT * FROM rejected_legs WHERE proposal_id = ?", (p['proposal_id'],))
                p['legs'] = [dict(row) for row in cursor.fetchall()]
            return proposals
    except Exception:
        return []

def get_autopsies():
    try:
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql_query("SELECT * FROM trade_autopsies ORDER BY timestamp DESC", conn)
    except Exception:
        return pd.DataFrame()

tab1, tab2, tab3 = st.tabs(["Live Portfolio & Ledger", "The Shadow Book (Risk Tracker)", "AI Trade Autopsies"])

with tab1:
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("The AI's Brain (Live Audit Ledger)")
        st.markdown("*Every single decision, rejection, and trade executed by the AI is permanently logged here. This is the un-editable proof of what the AI is thinking in real-time.*")
        df = get_audit_logs()
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No logs found. Waiting for a breaking news headline to trigger the AI...")

    with col2:
        st.subheader("Live Portfolio")
        st.markdown("*Real-world money on the line.*")
        account = get_alpaca_account()
        if account:
            equity = float(account.equity)
            last_equity = float(account.last_equity)
            equity_change = equity - last_equity
            equity_pct = (equity_change / last_equity) * 100 if last_equity else 0.0
            
            initial_margin = float(account.initial_margin)
            margin_utilization = (initial_margin / equity) * 100 if equity else 0.0
            
            st.metric("Account Equity", f"${equity:,.2f}", f"{equity_change:,.2f} ({equity_pct:.2f}%)")
            st.metric("Margin Utilization", f"{margin_utilization:.2f}%", None)
        else:
            st.metric("Account Equity", "$0.00", "0.00%")
            st.metric("Margin Utilization", "0.00%", "0.00%")
            
        st.metric("Net Delta", "0.00", "Neutral (Mocked)")

with tab2:
    st.subheader("The Shadow Book: Dodged Bullets & Saved Capital")
    st.markdown("What happens when our **AI Risk Officer** blocks a bad trade? We track it here to see exactly how much money the AI **saved you from losing**. It proves that good trading is just as much about the trades you *don't* take.")
    
    proposals = get_shadow_book()
    if not proposals:
        st.info("The Shadow Book is empty. Wait for the Risk Officer to reject a bad trade.")
    else:
        alpaca_client = AlpacaDataClient()
        
        for p in proposals:
            st.markdown(f"### {p['strategy_name']} on {p['symbol']}")
            st.write(f"**When:** {p['timestamp']}")
            st.write(f"**Why the AI blocked it:** {p['rejection_reason']}")
            
            contract_symbols = [leg['contract_symbol'] for leg in p['legs']]
            if not contract_symbols:
                continue
                
            try:
                snapshots = alpaca_client.get_option_snapshot(contract_symbols)
                current_mtm = 0.0
                for i, leg in enumerate(p['legs']):
                    quote = snapshots[i]
                    ask = quote.get("ask", 0.0)
                    bid = quote.get("bid", 0.0)
                    qty = leg["qty"]
                    if leg["side"] == "sell":
                        current_mtm -= (ask * qty)
                    else:
                        current_mtm += (bid * qty)
                
                initial_credit = p['initial_credit']
                profit = 0.0
                if initial_credit > 0:
                    profit = initial_credit + current_mtm
                else:
                    profit = current_mtm - abs(initial_credit)
                    
                col_a, col_b = st.columns(2)
                col_a.metric("Money We Would Have Risked", f"${abs(initial_credit):,.2f}")
                
                if profit < 0:
                    col_b.metric("Dodged Bullet (Capital Saved)", f"${abs(profit):,.2f}", "Good Rejection", delta_color="normal")
                else:
                    col_b.metric("Missed Opportunity (Lost)", f"-${profit:,.2f}", "Bad Rejection", delta_color="inverse")
            except Exception as e:
                st.warning(f"Could not fetch live prices for {contract_symbols}: {e}")
            
            st.markdown("---")

with tab3:
    st.subheader("AI Performance Reviews (Trade Autopsies)")
    st.markdown("When a trade finishes, the AI writes its own performance review. It analyzes the market data to explain exactly *why* it won or lost, proving it isn't just guessing.")
    
    autopsies_df = get_autopsies()
    if not autopsies_df.empty:
        for idx, row in autopsies_df.iterrows():
            with st.expander(f"Post-Mortem: {row['proposal_id']} ({row['timestamp']})"):
                st.markdown(row['report_markdown'])
    else:
        st.info("No reports available yet. Wait for a live trade to finish.")
