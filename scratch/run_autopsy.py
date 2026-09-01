import sqlite3
import os
import sys

sys.path.append(os.getcwd())

# Ensure we're in the right directory
if not os.path.exists("storage/audit.db"):
    print("Error: Could not find storage/audit.db. Make sure you run this from the project root.")
    sys.exit(1)

# Find the most recently closed trade
with sqlite3.connect("storage/audit.db") as conn:
    conn.row_factory = sqlite3.Row
    structure = conn.execute("SELECT proposal_id, strategy_name FROM structures WHERE status='closed' ORDER BY id DESC LIMIT 1").fetchone()

if not structure:
    print("No closed trades found in the database.")
    sys.exit(0)

proposal_id = structure["proposal_id"]
print(f"Found recently closed trade: {proposal_id} ({structure['strategy_name']})")
print("Starting Autopsy Agent...\n")

# Run the autopsy agent manually
from agents.autopsy_agent import run_autopsy
run_autopsy(proposal_id)

print("\nAutopsy complete! Check your Streamlit dashboard 'Trade Autopsies' tab.")
