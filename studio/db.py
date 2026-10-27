import sqlite3
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def connect(db_path: Path):
    """Short-lived connection; safe to use from LangGraph's worker threads."""
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        yield conn
        conn.commit()
    finally:
        conn.close()
