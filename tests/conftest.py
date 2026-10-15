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
    echtes_orig = {
        name: getattr(QMessageBox, name)
        for name in ("warning", "critical", "information", "question")
    }

    def still(selbst: object) -> int:
        """Bricht ab, wenn niemand aufpasst.

        Args:
            selbst: Der Dialog.

        Returns:
            ``0``, wie bei ``exec()``.
        """
        return 0

    QMessageBox.exec = still  # type: ignore[method-assign]
    # Die statischen Dialoge werden ohne Instanz gerufen, mit Fenster,
    # Titel und Text — deshalb die Sternchen.
    for name in ("warning", "critical", "information"):
        setattr(QMessageBox, name, staticmethod(lambda *a, **k: 0))
    QMessageBox.question = staticmethod(  # type: ignore[method-assign]
        lambda *a, **k: QMessageBox.StandardButton.Cancel
    )

    try:
        yield
    finally:
        QMessageBox.exec = echtes_exec  # type: ignore[method-assign]
        for name in ("warning", "critical", "information", "question"):
            setattr(QMessageBox, name, echtes_orig[name])


@pytest.fixture(autouse=True)
def fenster_zu() -> Iterator[None]:
    """Schliesst nach jedem Test alle Fenster.

    Ein Fenster, das offen bleibt, wird beim Abbau des Programms
    zerstoert — zu einem Zeitpunkt, zu dem Python schon halb weg ist.
    Qt kommt dann an Objekte, die es nicht mehr gibt, und beendet sich mit
    einem Busfehler statt mit einer Fehlermeldung.

    Gemessen, nicht vermutet: Sieben Tests in ``test_editor_fenster.py``
    endeten mit Signal 139 oder 135, alle mit einem offenen Fenster.

    Yields:
        Nichts.
    """
    pytest.importorskip("PySide6")
    from faktur.gui.qt import QApplication

    yield

    laufend = QApplication.instance()
    if laufend is None:
        return
    for fenster in list(laufend.topLevelWidgets()):
        fenster.close()
        fenster.deleteLater()
    laufend.processEvents()
