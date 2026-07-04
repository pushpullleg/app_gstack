"""Shared test fixtures."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from activity_logger.db import connection, migrations, seed


@pytest.fixture()
def db(tmp_path: Path) -> sqlite3.Connection:
    """In-memory-equivalent: temp-file DB, migrated, seeded, foreign_keys ON."""
    db_path = tmp_path / "test.db"
    conn = connection.connect(db_path)
    migrations.migrate(conn)
    seed.seed(conn)
    yield conn
    conn.close()


@pytest.fixture()
def empty_db(tmp_path: Path) -> sqlite3.Connection:
    """Temp-file DB with migrations applied but no seed data (no departments/codes)."""
    db_path = tmp_path / "empty_test.db"
    conn = connection.connect(db_path)
    migrations.migrate(conn)
    yield conn
    conn.close()


@pytest.fixture()
def seeded_db(tmp_path: Path) -> sqlite3.Connection:
    """Like db but in a separate tmp file — simulates a second install with same catalog, no entries."""
    db_path = tmp_path / "seeded_test.db"
    conn = connection.connect(db_path)
    migrations.migrate(conn)
    seed.seed(conn)
    yield conn
    conn.close()
