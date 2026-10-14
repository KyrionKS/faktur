"""Gemeinsame Vorbereitung für die Tests."""

from __future__ import annotations

import os
import sqlite3
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

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


@pytest.fixture(autouse=True)
def keine_offenen_dialoge() -> Iterator[None]:
    """Lässt keinen Dialog auf sich warten.

    ``QMessageBox.exec()`` blockiert, bis jemand klickt — im Testlauf
    klickt niemand. Ein Test, der eine Frage auslöst und sie nicht
    abfängt, hängt darum bis zum Ablauf des Zeitlimits, statt zu
    scheitern. Das ist teuer und sagt nichts: Nach fünfzehn Minuten
    steht da eine Zahl, aber nicht, **wo** es hängt.

    Deshalb beantwortet diese Vorrichtung von sich aus jede unbehandelte
    Frage mit *Abbrechen* — der vorsichtigste Antwort, die es gibt. Ein
    Test, der etwas anderes will, ersetzt sie ausdrücklich.

    Yields:
        Nichts.
    """
    pytest.importorskip("PySide6")
    from faktur.gui.qt import QMessageBox

    echtes_exec = QMessageBox.exec

    def still(selbst: object) -> int:
        """Bricht ab, wenn niemand aufpasst.

        Args:
            selbst: Der Dialog.

        Returns:
            ``0``, wie bei ``exec()``.
        """
        return 0

    QMessageBox.exec = still  # type: ignore[method-assign]
    try:
        yield
    finally:
        QMessageBox.exec = echtes_exec  # type: ignore[method-assign]
