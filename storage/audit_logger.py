import sqlite3
from datetime import datetime

class AuditLogger:
    """
    High-performance SQLite WAL (Write-Ahead Logging) audit trail.
    Ensures absolute traceability of AI decisions without blocking the main event loop.
    """
    def __init__(self, db_path: str = "storage/audit.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Enable WAL mode for high-concurrency writes without locking
            conn.execute("PRAGMA journal_mode=WAL;")
            # Relax synchronous mode for better write performance
            conn.execute("PRAGMA synchronous=NORMAL;")
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    details TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS structures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    net_credit_target REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id TEXT NOT NULL,
                    contract_symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    qty INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new',
                    filled_qty INTEGER DEFAULT 0,
                    filled_avg_price REAL DEFAULT 0.0,
                    FOREIGN KEY(proposal_id) REFERENCES structures(proposal_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rejected_proposals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    rejection_reason TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    initial_credit REAL NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rejected_legs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id TEXT NOT NULL,
                    contract_symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    qty INTEGER NOT NULL,
                    FOREIGN KEY(proposal_id) REFERENCES rejected_proposals(proposal_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trade_autopsies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id TEXT UNIQUE NOT NULL,
                    report_markdown TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

    def log_event(self, event_type: str, details: str):
        """Records an event to the immutable audit ledger."""
        timestamp = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO audit_logs (timestamp, event_type, details) VALUES (?, ?, ?)",
                (timestamp, event_type, details)
            )
            print(f"[AUDIT: {event_type}] {details}")

    def insert_structure(self, proposal_id: str, symbol: str, strategy_name: str, net_credit_target: float):
        timestamp = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO structures (proposal_id, symbol, strategy_name, net_credit_target, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (proposal_id, symbol, strategy_name, net_credit_target, 'open', timestamp)
            )

    def insert_order(self, proposal_id: str, contract_symbol: str, side: str, qty: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO orders (proposal_id, contract_symbol, side, qty, status) VALUES (?, ?, ?, ?, ?)",
                (proposal_id, contract_symbol, side, qty, 'new')
            )

    def update_order_fill(self, contract_symbol: str, side: str, filled_qty: int, filled_avg_price: float, new_status: str = 'filled'):
        """Updates the order status based on SSE fill events."""
        with sqlite3.connect(self.db_path) as conn:
            # We match on contract_symbol and side since we don't have the Alpaca order_id linked yet.
            # In a true prod system, we would map Alpaca client_order_id to our internal order ID.
            conn.execute(
                "UPDATE orders SET filled_qty = filled_qty + ?, filled_avg_price = ?, status = ? WHERE contract_symbol = ? AND side = ? AND status != 'closed'",
                (filled_qty, filled_avg_price, new_status, contract_symbol, side)
            )

    def update_structure_status(self, proposal_id: str, new_status: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE structures SET status = ? WHERE proposal_id = ?",
                (new_status, proposal_id)
            )

    def get_active_structures(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM structures WHERE status = 'open' OR status = 'filled'")
            return [dict(row) for row in cursor.fetchall()]

    def get_structure_orders(self, proposal_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM orders WHERE proposal_id = ?", (proposal_id,))
            return [dict(row) for row in cursor.fetchall()]

    def log_rejected_proposal(self, proposal_id: str, symbol: str, strategy_name: str, rejection_reason: str, initial_credit: float, legs: list):
        """Logs a rejected trade proposal into the Shadow Book."""
        timestamp = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO rejected_proposals (proposal_id, symbol, strategy_name, rejection_reason, timestamp, initial_credit) VALUES (?, ?, ?, ?, ?, ?)",
                (proposal_id, symbol, strategy_name, rejection_reason, timestamp, initial_credit)
            )
            for leg in legs:
                conn.execute(
                    "INSERT INTO rejected_legs (proposal_id, contract_symbol, side, qty) VALUES (?, ?, ?, ?)",
                    (proposal_id, leg["contract_symbol"], leg["side"], leg["ratio"])
                )

    def get_rejected_proposals(self):
        """Returns all rejected proposals for the Shadow Book UI."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM rejected_proposals")
            proposals = [dict(row) for row in cursor.fetchall()]
            for p in proposals:
                cursor = conn.execute("SELECT * FROM rejected_legs WHERE proposal_id = ?", (p['proposal_id'],))
                p['legs'] = [dict(row) for row in cursor.fetchall()]
            return proposals

    def log_autopsy(self, proposal_id: str, report_markdown: str):
        """Saves a trade autopsy report from the Autopsy Agent."""
        timestamp = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO trade_autopsies (proposal_id, report_markdown, timestamp) VALUES (?, ?, ?)",
                (proposal_id, report_markdown, timestamp)
            )
            
    def get_autopsies(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM trade_autopsies")
            return [dict(row) for row in cursor.fetchall()]
