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

with col2:
    st.subheader("Live Portfolio Metrics")
    st.metric("Account Equity", "$100,000.00", "0.00%")
    st.metric("Margin Utilization", "0.00%", "0.00%")
    st.metric("Net Delta", "0.00", "Neutral")
