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

tab1, tab2, tab3 = st.tabs(["Live Portfolio", "The Shadow Book", "Trade Autopsies"])

with tab1:
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Immutable Audit Ledger (WAL)")
        df = get_audit_logs()
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No audit logs found. Start `main.py` and wait for a catalyst to trigger the swarm.")

    with col2:
        st.subheader("Live Portfolio Metrics")
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
    st.subheader("The Shadow Book: Regret Minimization Tracker")
    st.markdown("Tracks the live P&L of trades the **Critic Agent** rejected. Proves the value of adversarial risk management.")
    
    proposals = get_shadow_book()
    if not proposals:
        st.info("The Shadow Book is empty. Wait for the Critic Agent to reject a proposed trade.")
    else:
        # Initialize Alpaca client for live prices
        alpaca_client = AlpacaDataClient()
        
        for p in proposals:
            st.markdown(f"### {p['strategy_name']} on {p['symbol']}")
            st.write(f"**Rejected At:** {p['timestamp']}")
            st.write(f"**Critic Reason:** {p['rejection_reason']}")
            
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
                col_a.metric("Hypothetical Entry Credit", f"${initial_credit:,.2f}")
                
                if profit < 0:
                    col_b.metric("Dodged Bullet (Saved)", f"${abs(profit):,.2f}", "Good Rejection", delta_color="normal")
                else:
                    col_b.metric("Missed Opportunity (Lost)", f"-${profit:,.2f}", "Bad Rejection", delta_color="inverse")
            except Exception as e:
                st.warning(f"Could not fetch live prices for {contract_symbols}: {e}")
            
            st.markdown("---")

with tab3:
    st.subheader("Autonomous Trade Autopsies")
    st.markdown("Post-mortem reports generated by the **Autopsy Agent** after a trade is closed by the Portfolio Manager.")
    
    autopsies_df = get_autopsies()
    if not autopsies_df.empty:
        for idx, row in autopsies_df.iterrows():
            with st.expander(f"Autopsy Report: {row['proposal_id']} ({row['timestamp']})"):
                st.markdown(row['report_markdown'])
    else:
        st.info("No autopsies available yet. Wait for a live trade to hit Take Profit or Stop Loss.")
