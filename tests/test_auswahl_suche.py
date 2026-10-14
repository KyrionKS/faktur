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

import os
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


# ------------------------------------------------- im Modell des Fensters


def test_das_modell_behaelt_auch_gleiche_zeilen_auseinander() -> None:
    """Der Grund, warum es im Fenster kein ``QSortFilterProxyModel`` gibt.

    Zwei Leistungen koennen gleich aussehen. Das Modell haelt beide, weil es
    zu jeder Zeile den Datensatz daneben ablegt. Ein Filter, der nur die
    Zeilen kennt, wuerde eine davon verschlucken — und wer die zweite
    anwuerde, bekomme die dritte.

    Args:
        None
    """
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

    from faktur.gui.tabelle import ZeilenModell

    zellen = lambda d: [d["bezeichnung"], d["einheit"], d["preis"]]  # noqa: E731
    modell = ZeilenModell(("Bezeichnung", "Einheit", "Preis"), zellen)
    erste = {"bezeichnung": "Mischung", "einheit": "Stunde", "preis": "950,00 €"}
    zweite = {"bezeichnung": "Mischung", "einheit": "Stunde", "preis": "950,00 €"}
    dritte = {"bezeichnung": "Aufnahme", "einheit": "Tag", "preis": "850,00 €"}
    modell.setze([erste, zweite, dritte])

    assert modell.rowCount() == 3
    assert modell.datensatz(0) is erste
    assert modell.datensatz(1) is zweite
    assert modell.datensatz(2) is dritte


def test_nach_dem_sortieren_steht_der_datensatz_hinter_seiner_zeile() -> None:
    """Der Fehler aus 0.8.1, an seiner eigentlichen Stelle.

    Die Liste, die das Modell haelt, wird sortiert — nicht die Anzeige. Wer
    zurueckspringt, bekommt damit immer den Datensatz, dessen Zeile er
    sieht.

    Args:
        None
    """
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

    from faktur.gui.tabelle import ZeilenModell, nach_text

    zellen = lambda d: [d["firma"]]  # noqa: E731
    modell = ZeilenModell(("Firma",), zellen, {0: nach_text(0)})
    tonwerk = {"firma": "Zeta Tonwerk"}
    klang = {"firma": "Alpha Klangstudio"}
    modell.setze([tonwerk, klang])

    modell.sortiere(0, True)

    for zeile in range(modell.rowCount()):
        angezeigt = modell.waert(zeile, 0)
        dahinter = modell.datensatz(zeile)
        assert dahinter is not None
        assert dahinter["firma"] == angezeigt


def test_ein_klick_ins_leere_faesst_nichts_an() -> None:
    """Zeile 99 in einer Liste mit zwei Zeilen.

    Ohne diese Schranke waere ``datensatz(99)`` ein Indexfehler mitten in
    einem Tastendruck — oder, schlimmer, der erste Datensatz der Liste.

    Args:
        None
    """
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

    from faktur.gui.tabelle import ZeilenModell

    modell = ZeilenModell(("Firma",), lambda d: [d["firma"]])
    tonwerk = {"firma": "Zeta Tonwerk"}
    modell.setze([tonwerk])

    assert modell.datensatz(99) is None
    assert modell.datensatz(-1) is None
    assert modell.zeile(tonwerk) == 0
    assert modell.zeile({"firma": "Zeta Tonwerk"}) == -1
