#!/usr/bin/env python3
"""Startet Faktur und richtet vorher alles ein, was fehlt.

Wer dieses Programm aus dem Netz holt, hat drei Dinge nicht: Python, eine
Umgebung und die drei Bibliotheken. Dieses Skript besorgt die beiden letzten
und sagt dir, was beim ersten Mal dauert.

    ./start.sh

Es ist danach weg. Beim zweiten Mal ist der ganze Weg eine Sekunde, weil
alles da ist. Nichts wird überschrieben, nichts geändert, was schon
stimmt.

Die Logik steht hier in Python und nicht in der Schale, weil man sie sonst
nicht prüfen könnte. ``tests/test_start.py`` geht jede Zeile davon durch,
ohne etwas zu starten.
"""

from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

#: Hier liegt das Programm. Nach dem Auspacken ist das der Ordner, in dem
#: das Skript steht.
WURZEL = Path(__file__).resolve().parent

#: Wohin die Umgebung kommt.
ORDNER_UMGEBUNG = WURZEL / ".venv"

#: Womit die Umgebung gestartet wird.
DATEI_LISTE = WURZEL / "requirements.txt"

#: Die kleinste Python-Version, mit der das Programm startet.
MINDESTVERSION = (3, 11)


#: Der Name ist deutsch wie alles andere hier. Die englische Endung auf
#: Fehlerbezeichnungen gibt es in diesem Projekt nicht, deshalb die Ausnahme.
class Fehler(Exception):  # noqa: N818
    """Etwas fehlt, das sich nicht beschaffen lässt.

    Steht als eigener Fehler, damit die Meldung oben im Klartext
    erscheint und nicht als Spur von einem Absturz.
    """


def python_aus_der_umgebung() -> Path:
    """Nennt den Interpreter in der eigenen Umgebung.

    Returns:
        Der Pfad zum Python.
    """
    if os.name == "nt":  # pragma: no cover - unter Windows nicht benutzt
        return ORDNER_UMGEBUNG / "Scripts" / "python.exe"
    return ORDNER_UMGEBUNG / "bin" / "python"


def umgebung_fehlt() -> bool:
    """Sagt, ob die Umgebung noch nicht angelegt ist.

    Nicht ob etwas darin fehlt: das merkt der Aufrufer beim Start von
    Programmen.

    Returns:
        ``True``, wenn noch keine Umgebung da ist.
    """
    return not python_aus_der_umgebung().is_file()


def lege_umgebung_an() -> None:
    """Legt die Umgebung an und holt die Bibliotheken.

    Raises:
        Fehler: Wenn Python zu alt ist oder das Anlegen nicht gelingt.
    """
    if sys.version_info < MINDESTVERSION:
        raise Fehler(_text_zu_altes_python(sys.version_info))

    try:
        venv.EnvBuilder(with_pip=True).create(ORDNER_UMGEBUNG)
    except Exception as cause:  # noqa: BLE001
        raise Fehler(_text_fehlgeschlagenes_anlegen(cause)) from cause

    _installiere()


def _installiere() -> None:
    """Holt die Bibliotheken aus der eigenen Umgebung.

    Läuft bei jedem Start, ist aber im Normalfall in zwei Sekunden fertig.
    Das ist billiger, als zu raten, ob noch etwas fehlt.

    Raises:
        Fehler: Wenn die Bibliotheken nicht zu bekommen sind.
    """
    if not DATEI_LISTE.is_file():
        raise Fehler(
            f"Die Datei {DATEI_LISTE.name} fehlt. Ohne sie ist nicht zu "
            "wissen, welche Bibliotheken das Programm braucht."
        )

    ergebnis = subprocess.run(  # noqa: S603
        [
            str(python_aus_der_umgebung()),
            "-m",
            "pip",
            "install",
            "--quiet",
            "--disable-pip-version-check",
            "-r",
            str(DATEI_LISTE),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    if ergebnis.returncode != 0:
        raise Fehler(_text_fehlgeschlagene_bibliotheken(ergebnis.stderr))


def hole_datenbank() -> Path:
    """Nennt die Datenbank, falls sie schon da ist.

    Returns:
        Der Pfad, oder ``None``, wenn das Programm noch nie lief.
    """
    from faktur import orte

    datei = orte.datenbank()
    return datei if datei.is_file() else None


def logo_fehlt() -> bool:
    """Sagt, ob das Logo für die PDF fehlt.

    Returns:
        ``True``, wenn die PDF ohne Bild auskämen.
    """
    from faktur import orte

    return not orte.logo().is_file()


def text_start() -> str:
    """Was beim ersten Start gesagt wird.

    Returns:
        Ein kurzer Text für das Terminal.
    """
    if hole_datenbank() is None:
        return (
            "Erster Start. Die Bibliotheken werden einmal geholt, das dauert "
            "etwas.\nDanach geht es sofort los."
        )
    return "Faktur 0.4.0"


def text_logo() -> str:
    """Der Hinweis auf das fehlende Logo.

    Returns:
        Ein Satz, oder ``""``, wenn das Logo da ist.
    """
    if not logo_fehlt():
        return ""
    return (
        "Hinweis: ohne Logo kommen die PDF ohne Bild. Die Datei logo.png "
        "gehört in den Ordner daten/ neben dem Programm."
    )


def starte() -> int:
    """Startet das Programm und wartet auf sein Ende.

    Der Interpreter wird an die Stelle des Skripts gesetzt, nicht als Kind
    daneben. Sonst hätte man nach dem Beenden noch das Terminal voller
    Rauschen.

    Returns:
        Der Rückgabewert des Programms.
    """
    befehl = [str(python_aus_der_umgebung()), "-m", "faktur"]

    if os.name != "nt":  # pragma: no branch - unter Windows nicht benutzt
        # exec() gibt den Platz im Terminal ab. Strg+C kommt dann direkt im
        # Programm an und beendet es sauber.
        os.execv(befehl[0], befehl)

    return subprocess.run(befehl, check=False).returncode


def main() -> int:
    """Richtet ein und startet.

    Returns:
        ``0``, wenn das Programm sauber beendet wurde.
    """
    print(text_start(), flush=True)

    try:
        if umgebung_fehlt():
            lege_umgebung_an()
        else:
            _installiere()

        hinweis = text_logo()
        if hinweis:
            print(hinweis, flush=True)

    except Fehler as cause:
        print(f"\n{cause}", file=sys.stderr, flush=True)
        return 1

    return starte()


def _text_zu_altes_python(ist: tuple[int, ...]) -> str:
    """Erklärt, was mit dem Python los ist.

    Args:
        ist: Die vorhandene Version.

    Returns:
        Ein Text für das Terminal.
    """
    noetig = ".".join(str(teil) for teil in MINDESTVERSION)
    da = ".".join(str(teil) for teil in ist[:3])
    return (
        f"Faktur braucht Python {noetig} oder neuer. Hier läuft {da}.\n\n"
        "Ein neues Python holen:\n"
        "  macOS:   brew install python@3.12\n"
        "  Ubuntu:  sudo apt install python3-venv python3.12\n"
        "Danach ./start.sh noch einmal."
    )


def _text_fehlgeschlagenes_anlegen(cause: Exception) -> str:
    """Erklärt, warum die Umgebung nicht entstanden ist.

    Args:
        cause: Die Ausnahme aus der Bibliothek.

    Returns:
        Ein Text für das Terminal.
    """
    beispiel = "ensurepip" in str(cause) or "pip" in str(cause).lower()
    if beispiel:
        return (
            "Die Umgebung konnte nicht angelegt werden, weil im Python das "
            "Modul für pip fehlt.\n\n"
            "Auf einem Mac:\n"
            "  brew install python@3.12\n"
            "Auf einem Ubuntu:\n"
            "  sudo apt install python3-venv\n"
            f"Die Meldung lautete: {cause}"
        )
    return f"Die Umgebung konnte nicht angelegt werden.\n\nDie Meldung lautete: {cause}"


def _text_fehlgeschlagene_bibliotheken(rueckmeldung: str) -> str:
    """Erklärt, warum die Bibliotheken nicht kamen.

    Args:
        rueckmeldung: Die Ausgabe von pip.

    Returns:
        Ein Text für das Terminal.
    """
    roh = rueckmeldung.strip().splitlines()
    letzte = roh[-1] if roh else "keine Angabe"
    return (
        "Die Bibliotheken konnten nicht geholt werden.\n\n"
        "Steht dort etwas von 'externally-managed-environment', dann ist die "
        "Umgebung nicht angelegt worden.\n"
        "Steht dort 'No matching distribution found', passt die Python-Version "
        "nicht.\n\n"
        f"Die Meldung lautete: {letzte}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
