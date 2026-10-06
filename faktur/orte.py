"""Wo die Daten liegen.

Alles liegt in einem Ordner ``daten`` neben dem Programm. Also immer neben
dem Ordner ``faktur``, egal von wo du startest:

    /Users/kyrion/Vibecoding/faktur/daten/faktur.db

Das ist der Punkt: Das Programm wird aus dem Quelltext gestartet, und der
Quelltext kann von überall kommen. Ein ``~/Library/Application Support``-Pfad
wäre stabiler, läge aber an einer Stelle, die man nicht wiederfindet. Ein
Ordner neben dem Programm ist genau da, wo man ihn sucht.

``daten/`` steht in der ``.gitignore`` und wird mitveröffentlicht, wenn er
versehentlich committet wird.
"""

from __future__ import annotations

from pathlib import Path

#: Wie der Datenordner heißt.
DATENORDNERNAME = "daten"

#: Wo der Quelltext liegt. Die Dateien eine Ebene über dem Paket.
WURZEL = Path(__file__).resolve().parent.parent


def datenordner() -> Path:
    """Gibt den Ordner zurück, in dem Datenbank, Logo und Dokumente liegen.

    Returns:
        Der Ordner ``daten`` neben dem Programm.
    """
    return WURZEL / DATENORDNERNAME


def datenbank() -> Path:
    """Gibt den Pfad der Datenbank zurück.

    Returns:
        Die Datei im Datenordner.
    """
    return datenordner() / "faktur.db"


def logo() -> Path:
    """Gibt den erwarteten Pfad des Logos zurück.

    Returns:
        Die Datei im Datenordner. Vorhanden sein muss sie nicht.
    """
    return datenordner() / "logo.png"


def dokumente() -> Path:
    """Gibt den Ordner für die PDF zurück.

    Returns:
        Der Ordner im Datenordner.
    """
    return datenordner() / "Dokumente"
