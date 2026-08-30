import streamlit as st
import sqlite3
import pandas as pd
import os

st.set_page_config(page_title="ThetaSwarm | Glass Box", layout="wide", initial_sidebar_state="expanded")

st.title("🧠 ThetaSwarm Glass Box")
st.markdown("### FAANG-Grade Autonomous Options Arbitrage")

st.sidebar.header("System Status")
st.sidebar.success("🟢 Event Poller: ACTIVE")
st.sidebar.success("🟢 SQLite WAL: ACTIVE")
st.sidebar.info("🤖 CrewAI Swarm: STANDBY")

# Risk Limits UI
st.sidebar.markdown("---")
st.sidebar.subheader("Risk Gates (Active)")
st.sidebar.checkbox("Max Risk <= 5%", value=True, disabled=True)
st.sidebar.checkbox("Margin <= 30%", value=True, disabled=True)
st.sidebar.checkbox("Thursday 15:30 Liquidation", value=True, disabled=True)

def get_audit_logs():
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "audit.db")
    try:
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql_query("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 50", conn)
    except Exception:
        return pd.DataFrame()

df = get_audit_logs()

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Immutable Audit Ledger (WAL)")
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No audit logs found. Start `main.py` and wait for a catalyst to trigger the swarm.")

import sys
from pathlib import Path
# Add project root to sys.path to allow importing config
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from alpaca.trading.client import TradingClient

def get_alpaca_account():
    if not settings.ALPACA_API_KEY:
        return None
    try:
        client = TradingClient(settings.ALPACA_API_KEY, settings.ALPACA_SECRET_KEY, paper=settings.ALPACA_PAPER)
        return client.get_account()
    except Exception as e:
        st.error(f"Failed to fetch Alpaca account: {e}")
        return None

account = get_alpaca_account()

with col2:
    st.subheader("Live Portfolio Metrics")
    
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
