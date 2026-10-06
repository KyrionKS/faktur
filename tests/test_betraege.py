"""Tests für Geldbeträge und Datumsangaben."""

from __future__ import annotations

import datetime

import pytest
from faktur import betraege


@pytest.mark.parametrize(
    ("eingabe", "erwartet"),
    [
        ("1.234,50", 1234.50),
        ("1.234", 1234.0),
        ("1234.50", 1234.50),
        ("1.234,56 €", 1234.56),
        ("850", 850.0),
        ("1,5", 1.5),
        ("", 0.0),
        (None, 0.0),
        ("keine Zahl", 0.0),
        (850.0, 850.0),
    ],
)
def test_zahl_liest_eingaben(eingabe: object, erwartet: float) -> None:
    """Liest die üblichen Schreibweisen.

    Args:
        eingabe: Die Eingabe.
        erwartet: Der Betrag, der herauskommen soll.
    """
    assert betraege.zahl(eingabe) == pytest.approx(erwartet)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("wert", "erwartet"),
    [
        (0.0, "0,00 €"),
        (850.0, "850,00 €"),
        (3290.0, "3.290,00 €"),
        (1234567.89, "1.234.567,89 €"),
        (95.5, "95,50 €"),
    ],
)
def test_euro_formatiert_deutsch(wert: float, erwartet: str) -> None:
    """Setzt Punkt und Komma an die richtige Stelle.

    Args:
        wert: Der Betrag.
        erwartet: Der Text.
    """
    assert betraege.euro(wert) == erwartet


@pytest.mark.parametrize(
    ("wert", "erwartet"),
    [(1.0, "1"), (2.5, "2,5"), (3.0, "3"), (0.25, "0,25")],
)
def test_menge_ohne_nutzlose_stellen(wert: float, erwartet: str) -> None:
    """Lässt Nachkommastellen weg, wenn sie nichts sagen.

    Args:
        wert: Die Menge.
        erwartet: Der Text.
    """
    assert betraege.menge(wert) == erwartet


def test_datum_aus_verschiedenen_schreibweisen() -> None:
    """Liest alle Formate, die beim Tippen herauskommen."""
    assert betraege.datum("06.10.2026") == "06.10.2026"
    assert betraege.datum("2026-10-06") == "06.10.2026"
    assert betraege.datum("6.10.26") == "06.10.2026"
    assert betraege.datum("kein Datum") == ""
    assert betraege.datum("") == ""


def test_plus_tage_rechnet_von_heute() -> None:
    """Rechnet vom Ausgangstag aus weiter."""
    start = datetime.date(2026, 10, 6)
    assert betraege.plus_tage(14, start) == "20.10.2026"
    assert betraege.plus_tage(-6, start) == "30.09.2026"


def test_euro_rundet_kaufmaennisch() -> None:
    """Rundet auf die zweite Stelle, nicht auf Bytes."""
    assert betraege.euro(0.005) == "0,01 €"
    assert betraege.euro(1.005) == "1,01 €"
    assert betraege.euro(3290.004) == "3.290,00 €"
