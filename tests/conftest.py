"""Gemeinsame Vorbereitung für die Tests."""

from __future__ import annotations

import sqlite3
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from faktur import db  # noqa: E402


@pytest.fixture
def verbindung(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """Legt eine frische Datenbank für jeden Test an.

    Args:
        tmp_path: Das temporäre Verzeichnis von pytest.

    Yields:
        Die offene Verbindung. Wird nach dem Test geschlossen.
    """
    test = db.verbinden(tmp_path / "faktur.db")
    yield test
    test.close()
