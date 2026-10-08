"""Tests für die Versionsangabe.

Die Nummer steht an zwei Stellen: in ``faktur/__init__.py``, wo das Programm
sie beim Start kennt, und in ``pyproject.toml``, wo man sie zum Einpacken
braucht. Solange das nur eine Angabe wäre, wäre es einfach. Zwei sind es
geworden, und sie sind auseinandergegangen: das Paket meldete 0.3, das
Programm 0.1.

Dieser Test verhindert das. Er ist der Grund, warum die Doppelangabe
erlaubt ist.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from faktur import __version__

WURZEL = Path(__file__).resolve().parents[1]


def _angabe_aus_der_pyproject() -> str:
    """Liest die Version aus der pyproject.toml.

    Returns:
        Die Versionsangabe als Text.
    """
    daten = tomllib.loads((WURZEL / "pyproject.toml").read_text(encoding="utf-8"))
    return str(daten["project"]["version"])


def test_beide_stellen_sagen_dasselbe() -> None:
    """Der Kern des Ganzen.

    Ein Runtestschlag hier bedeutet: vor dem Veröffentlichen die eine
    Stelle angleichen.
    """
    assert __version__ == _angabe_aus_der_pyproject(), (
        f"faktur/__init__.py sagt {__version__}, "
        f"pyproject.toml sagt {_angabe_aus_der_pyproject()}."
    )


def test_die_angabe_ist_eine_versionsnummer() -> None:
    """Drei Teile, aus Zahlen. Sonst ist es etwas anderes als eine Nummer.

    Ohne diese Form lädt die Schnittstelle von PyPI das Paket nicht, und
    ein Tippfehler wie ``0,4`` bliebe sonst unentdeckt.
    """
    teile = __version__.split(".")

    assert len(teile) == 3, f"'{__version__}' ist keine Form wie 0.4.0"
    assert all(teil.isdigit() for teil in teile), (
        f"'{__version__}' enthaelt etwas anderes als Ziffern."
    )


def test_die_version_ist_nicht_leer() -> None:
    """Leer gilt als ausgelassen, nicht als Platzhalter."""
    assert __version__.strip() != ""


@pytest.mark.parametrize(
    "datei",
    ["README.md", "docs/ANLEITUNG.md", "docs/BEDIENUNG.md"],
)
def test_die_texte_nennen_keine_feste_versionsnummer(datei: str) -> None:
    """Kein Dokument schreibt eine Nummer fest.

    Sobald eine Version hochgeht, sind es drei Stellen: Paket, Programm und
    Anleitung. Die Anleitung zeigt deshalb auf die Release-Seite, wo die
    Nummer automatisch stimmt.

    Args:
        datei: Der Text, der geprüft wird.
    """
    pfad = WURZEL / datei
    if not pfad.is_file():
        pytest.skip(f"{datei} gibt es nicht")

    gefunden = [
        zeile.strip()
        for zeile in pfad.read_text(encoding="utf-8").splitlines()
        if zeile.strip().startswith("Version")
        and any(ziffer in zeile for ziffer in "0123456789")
    ]

    assert gefunden == [], (
        f"{datei} schreibt eine Versionsnummer fest: {gefunden}. "
        "Besser auf die Release-Seite verweisen."
    )
