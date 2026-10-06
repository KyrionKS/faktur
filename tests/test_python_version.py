"""Prüft die angesetzte Mindestversion von Python.

Der Wert in ``pyproject.toml`` ist eine Zusage an Menschen, die das Programm
auf ihrem Rechner installieren. Steigt er unbemerkt, scheitert die
Installation an einer Stelle, die mit dem Programm nichts zu tun hat.

Der Code kommt nachweislich mit Python 3.10 durch, die Abhängigkeiten
ebenfalls. Der Ansatz gilt nur als Untergrenze für die Werkzeuge im
Repository.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

#: Der Ansatz, der gelten soll.
MINDESTVERSION = (3, 11)

#: Womit der Code nachweislich auskommt. Alles darüber ist Reichtum.
BEWEISBAR_MIT = (3, 10)

WURZEL = Path(__file__).resolve().parents[1]


def _angesetzt() -> tuple[int, int]:
    """Liest den Ansatz aus der pyproject.toml.

    Returns:
        Die Version als Paar aus Haupt- und Nebennummer.
    """
    daten = tomllib.loads((WURZEL / "pyproject.toml").read_text(encoding="utf-8"))
    roh = daten["project"]["requires-python"].lstrip(">=")
    haupt, _, rest = roh.partition(".")
    return (int(haupt), int(rest.split(".")[0]))


def test_pyproject_nennt_die_mindestversion() -> None:
    """Die Datei sagt, was sie sagt."""
    assert _angesetzt() == MINDESTVERSION


def test_der_code_kommt_mit_py310_durch() -> None:
    """Kein Quelltext braucht Syntax, die es vor 3.10 nicht gab.

    Das ist der Grund, warum der Ansatz so tief liegen darf. Fällt diese
    Prüfung, weil jemand eine neuere Schreibweise benutzt, muss der Ansatz
    mit hoch.
    """
    schlecht: list[str] = []

    for datei in sorted(WURZEL.rglob("*.py")):
        if ".venv" in datei.parts or "daten" in datei.parts:
            continue
        quelle = datei.read_text(encoding="utf-8")
        try:
            ast.parse(quelle, filename=str(datei), feature_version=BEWEISBAR_MIT)
        except SyntaxError as fehler:
            schlecht.append(f"{datei.relative_to(WURZEL)}: {fehler.msg}")

    assert schlecht == [], (
        "Diese Dateien brauchen eine neuere Python-Version: " + "; ".join(schlecht)
    )
