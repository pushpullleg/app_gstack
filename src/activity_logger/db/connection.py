"""SQLite connection factory with WAL mode, FK enforcement, and startup writability check."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from activity_logger import config


def _check_writable(path: Path) -> None:
    """Raise RuntimeError if the directory containing path is not writable."""
    directory = path.parent
    directory.mkdir(parents=True, exist_ok=True)
    if not os.access(directory, os.W_OK):
        raise RuntimeError(
            f"Cannot write to data directory: {directory}\n"
            "Check folder permissions or set ACTIVITY_LOGGER_HOME to a writable path."
        )


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Return a configured SQLite connection. Raises RuntimeError if dir is not writable."""
    path = db_path or config.DB_PATH
    _check_writable(path)

    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")

    return conn
