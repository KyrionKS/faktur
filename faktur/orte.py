"""Wo die Daten liegen.

Aus dem Quelltext liegt der Datenordner neben dem Programm. In einem
gebauten Programm sieht das anders aus: Dort steckt der Einstiegspunkt in
``Faktur.app/Contents/MacOS/Faktur``, und Daten neben ihm zu schreiben hieße,
sie in das Programm zu schreiben. Das gehört dem System und wird bei einem
Update ersetzt.

Darum wird nicht über ``..`` hochgezählt — das hinge an einer bestimmten
Bundle-Struktur. Gesucht wird die Komponente, die auf ``.app`` endet, und der
Datenordner kommt daneben:

    /Users/kyrion/Faktur/Faktur.app/Contents/MacOS/Faktur   <- der Einstieg
    /Users/kyrion/Faktur/daten/faktur.db                    <- und hierhin

Wichtig: gerechnet wird vom Pfad des Programms, nicht vom Arbeitsverzeichnis.
Beim Doppelklick auf ein Programm ist das Arbeitsverzeichnis irgendwo
sonst, und die Daten landeten dort, wo niemand sie sucht.
"""

from __future__ import annotations

import sys
from pathlib import Path

#: Wie der Datenordner heißt. Überall gleich, damit man ihn auf Anhieb
#: findet und nicht je nach Betriebssystem suchen muss.
DATENORDNERNAME = "daten"


def im_bundle() -> bool:
    """Sagt, ob das Programm als gebautes Programm läuft.

    Returns:
        ``True``, wenn ein Packer das Programm zusammengesetzt hat.
    """
    return bool(getattr(sys, "frozen", False))


def neben_programm(einstieg: Path) -> Path:
    """Findet den Ordner, neben dem die Daten gehören.

    Args:
        einstieg: Der Pfad zur ausführbaren Datei.

    Returns:
        Bei einem Bundle der Ordner, der die ``.app`` enthält. Sonst der
        Elternordner der Datei.
    """
    for nummer, teil in enumerate(einstieg.parts):
        if teil.endswith(".app"):
            return Path(*einstieg.parts[:nummer])

    return einstieg.parent


def datenordner() -> Path:
    """Gibt den Ordner zurück, in dem Datenbank, Logo und Dokumente liegen.

    Der heißt überall gleich. Im Bundle also nicht direkt neben der ``.app``,
    sondern eine Stufe weiter: Daten, die unmittelbar neben dem Programm
    liegen, übersieht man beim Suchen.

    Returns:
        Der Ordner ``daten`` neben dem Programm.
    """
    if im_bundle():
        return neben_programm(Path(sys.executable).resolve()) / DATENORDNERNAME
    return Path(__file__).resolve().parent.parent / DATENORDNERNAME


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
