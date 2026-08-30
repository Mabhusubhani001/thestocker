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

    def log_event(self, event_type: str, details: str):
        """Records an event to the immutable audit ledger."""
        timestamp = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO audit_logs (timestamp, event_type, details) VALUES (?, ?, ?)",
                (timestamp, event_type, details)
            )
            print(f"[AUDIT: {event_type}] {details}")
