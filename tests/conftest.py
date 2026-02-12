"""Shared test fixtures for the workflow orchestrator test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add project root to path so package imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import db


@pytest.fixture
def fresh_db(tmp_path):
    """Fresh DB for isolated tests."""
    db_path = tmp_path / "state.db"
    db.init_db("TestProject", db_path=db_path)
    conn = db.get_db(db_path)
    yield conn
    conn.close()
