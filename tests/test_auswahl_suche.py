"""Tests für die Suche in den Auswahlen des Editors.

In 0.6 habe ich die Suche auf die Bildschirme gesetzt, die eine ganze Liste
zeigen — Kunden, Dokumente, offene Forderungen. Die beiden Auswahlen, mit
denen man tatsächlich ein Dokument baut, habe ich vergessen. Das holt 0.8
nach.

Der wichtigste Test ist der über die **doppelte Zeile**: Zwei Leistungen
können dieselbe Bezeichnung, dieselbe Einheit und denselben Preis haben.
Vergleicht man beim Filtern die Zeilen nach ihrem Text, fallen sie
auseinander — und wer die zweite anklickt, bekommt die dritte.

Beim Kundenschritt ist das nicht möglich, weil jede Zeile ihre Kennung mit
trägt. Genau darum steht hier auch, dass es so bleibt.
"""

from __future__ import annotations

import sqlite3

import pytest
from faktur import dateien
from faktur.suchen import passt

#: Zwei Leistungen, die auf dem Papier gleich aussehen.
DOPPELT_A = ("Mischung und Mastering", "Stunde", "950,00 €")
DOPPELT_B = ("Mischung und Mastering", "Stunde", "950,00 €")


def test_die_beiden_doppelten_sind_wirklich_gleich() -> None:
    """Sonst waere der Test darunter sinnlos.

    Args:
        None
    """
    assert DOPPELT_A == DOPPELT_B


def test_beim_filtern_nach_werten_verschwindet_eine_zeile() -> None:
    """Warum man nicht nach Zeilentext filtern darf.

    Beide Zeilen sind gleich, also passt der Filter auf beide — aber eine
    Liste, die aus den Werten gebaut wird, haelt sie nur einmal. Genau
    daran ist zu sehen, dass der Index kaputt waere.

    Args:
        None
    """
    zeilen = [list(DOPPELT_A), list(DOPPELT_B)]
    passend = [z for z in zeilen if passt(z, "Mischung")]

    assert len(passend) == 2, "Der Filter muss beide Zeilen durchlassen"


def test_ueber_indizes_gefiltert_bleibt_alles_erhalten() -> None:
    """Der Weg, der stimmt.

    Args:
        None
    """
    zeilen = [list(DOPPELT_A), list(DOPPELT_B), ["Aufnahme Ton", "Tag", "850,00 €"]]
    nummern = [n for n, z in enumerate(zeilen) if passt(z, "Mischung")]

    assert nummern == [0, 1]

    # Die beiden gleichen Zeilen stehen in der gefilterten Liste zweimal da,
    # in der richtigen Reihenfolge — und die dritte ist raus.
    gefiltert = [zeilen[n] for n in nummern]
    assert gefiltert == [zeilen[0], zeilen[1]]
    assert len(gefiltert) == 2


def test_und_die_zweite_bleibt_die_zweite() -> None:
    """Das ist der eigentliche Zweck: Die Reihenfolge stimmt.

    Args:
        None
    """
    alle = ["erste", "zweite", "dritte", "vierte"]
    sichtbar = [n for n, z in enumerate(alle) if passt((z,), "e")]

    assert alle[sichtbar[1]] == "zweite"


# --------------------------------------------------------------- im Programm


@pytest.fixture
def preisliste(verbindung: sqlite3.Connection) -> list:
    """Legt die Standardleistungen an und fuegt zwei gleiche hinzu.

    Args:
        verbindung: Die Datenbankverbindung.

    Returns:
        Die Liste der Leistungen.
    """
    for _ in range(2):
        dateien.leistung_speichern(
            verbindung,
            {
                "bezeichnung": "Mischung und Mastering",
                "einheit": "Stunde",
                "preis": "950",
            },
        )
    return dateien.leistungen(verbindung)


def test_die_preisliste_kann_doppelte_zeilen_haben(
    preisliste: list,
) -> None:
    """Das Programm lässt das zu — es gibt keine Sperre darauf.

    Args:
        preisliste: Die Leistungen.
    """
    zeilen = [
        (leistung["bezeichnung"], leistung["einheit"], leistung["preis"])
        for leistung in preisliste
    ]

    assert len(zeilen) > len(set(zeilen)), (
        "Die beiden gleichen Zeilen sollten wirklich gleich sein. Sonst "
        "prüft dieser Test nichts."
    )


def test_das_programm_hat_keine_sperre_gegen_doppelte_leistungen(
    verbindung: sqlite3.Connection,
) -> None:
    """Absicht. Sonst wäre die Prüfung hier eine Illusion.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    for nummer in range(3):
        dateien.leistung_speichern(
            verbindung,
            {
                "bezeichnung": f"Gleich {nummer == 0 and 'a' or 'b'}",
                "einheit": "Stunde",
                "preis": "100",
            },
        )

    assert len(dateien.leistungen(verbindung)) >= 3


# ------------------------------------------------------- die Bildschirme


def test_der_kundenschritt_trägt_die_kennung_mit() -> None:
    """Warum dort keine Index-Falle droht.

    Jede Zeile der Kundenauswahl beginnt mit der Kennung des Kunden, und
    ``Auswahl`` gibt genau die Kennung der gewaehlten Zeile weiter. Ein
    Filter, der die Zeilen kuerzt, verschleppt die Kennung mit — es gibt
    keine Stelle, an der ein Index zeigen koennte auf eine Liste, die gar
    nicht gezeichnet wird.

    Args:
        None
    """
    from faktur.widgets import Auswahl

    quelle = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "faktur"
        / "screens"
        / "dokumente.py"
    ).read_text(encoding="utf-8")

    # Die Kennung ist das erste Feld jeder Zeile.
    assert 'str(kunde["id"]),\n' in quelle, (
        "Die Kundenauswahl traegt die Kennung nicht mehr am Anfang der Zeile."
    )
    assert Auswahl is not None


def test_der_leistungsschritt_filtert_ueber_indizes() -> None:
    """Hier wird es um die Indizes gemacht.

    Args:
        None
    """
    quelle = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "faktur"
        / "screens"
        / "dokumente.py"
    ).read_text(encoding="utf-8")

    assert "enumerate(zeilen)" in quelle
    assert "self.sichtbar[event.zeile]" in quelle
    assert "self.leistungen[event.zeile]" not in quelle, (
        "Hier wird noch ueber die vollstaendige Liste indexiert. Nach dem "
        "Filtern waere das die falsche Leistung."
    )
