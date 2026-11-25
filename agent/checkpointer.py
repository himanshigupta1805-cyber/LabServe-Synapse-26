"""
Checkpointer — State Persistence
==================================
Creates a checkpointer for LangGraph so that interrupted runs (e.g.
awaiting Chief's approval) can resume with full state.
"""

import os
import sqlite3


def create_checkpointer(db_path: str | None = None):
    """Create and return a LangGraph checkpointer.

    Tries SqliteSaver first; falls back to InMemorySaver if SQLite
    setup fails.

    Args:
        db_path: Path to the SQLite database.  Defaults to env var
                 CHECKPOINT_DB or './checkpoints.db'.

    Returns:
        A checkpointer instance ready for graph compilation.
    """
    path = db_path or os.getenv("CHECKPOINT_DB", "./checkpoints.db")

    try:
        # Try SQLite-based persistence
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
        except ImportError:
            from langgraph_checkpoint_sqlite import SqliteSaver  # type: ignore[import]

        conn = sqlite3.connect(path, check_same_thread=False)
        saver = SqliteSaver(conn)
        return saver
    except Exception:
        # Fall back to in-memory checkpointer
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
