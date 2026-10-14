"""Anlegen, ändern, stilllegen, löschen.

Bis hierher konnte das Fenster nur lesen. Diese Datei prüft, dass man
jetzt auch schreiben kann — und vor allem, dass die vier Aktionen an den
**richtigen** Datensatz gehen.

Denn das ist genau der Fehler aus 0.8.1: Man sah *Zeta Tonwerk*, tippte
``Entf``, und *Alpha Klangstudio* war weg. Hier wird jede Aktion gegen
einen Kunden geprüft, der gar nicht auf dem Bildschirm steht.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

from faktur import dateien  # noqa: E402
from faktur.gui.fenster import Fenster  # noqa: E402


@pytest.fixture
def app() -> object:
    """Gibt die laufende Qt-Anwendung zurück.

    Returns:
        Die Anwendung.
    """
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def fenster(app: object, tmp_path: Path) -> object:
    """Baut ein Fenster mit einer frischen Datenbank.

    Returns:
        Das Fenster.
    """
    fenster = Fenster(dateien and None or _verbindung(tmp_path))
    fenster.zeige()
    app.processEvents()  # type: ignore[attr-defined]
    return fenster


def _verbindung(tmp_path: Path) -> sqlite3.Connection:
    """Öffnet eine frische Datenbank.

    Args:
        tmp_path: Das Verzeichnis fuer die Datei.

    Returns:
        Die offene Verbindung.
    """
    from faktur import db

    return db.verbinden(tmp_path / "formular.db")


def _kunden(fenster: object) -> object:
    """Öffnet die Kundenliste.

    Args:
        fenster: Das Fenster.

    Returns:
        Die Kundenliste.
    """
    fenster.gehe("kunden")  # type: ignore[attr-defined]
    return fenster.seiten["kunden"]  # type: ignore[attr-defined]


def _waehle(seite: object, spalte: int, gesucht: str) -> object:
    """Markiert die Zeile, die in einer Spalte etwas Bestimmtes zeigt.

    So wie ein Klick: gesucht wird im **Anzeigetext**, nicht im
    Datensatz. Wer statt dessen über die Identität des Datensatzes geht,
    prüft einen anderen Weg als den, den ein Benutzer nimmt — und genau
    daran ist der Fehler aus 0.8.1 nicht aufgefallen.

    Args:
        seite: Die Liste.
        spalte: Die Spalte, in der gesucht wird.
        gesucht: Der Text, nach dem gesucht wird.

    Returns:
        Der Datensatz der gefundenen Zeile.

    Raises:
        AssertionError: Wenn keine Zeile passt.
    """
    for zeile in range(seite.modell.rowCount()):
        if seite.modell.waert(zeile, spalte) == gesucht:
            seite.ansicht.setCurrentIndex(seite.modell.index(zeile, spalte))
            return seite.modell.datensatz(zeile)
    gefunden = [
        seite.modell.waert(zeile, spalte) for zeile in range(seite.modell.rowCount())
    ]
    raise AssertionError(f"„{gesucht}“ steht nicht in der Liste. Angezeigt: {gefunden}")


# ------------------------------------------------------- Stilllegen in der Logik


def test_ein_stillgelegter_kunde_verschwindet_aus_der_liste(
    fenster: object,
) -> None:
    """Stilllegen ist nicht Löschen: der Satz bleibt in der Datenbank.

    Args:
        fenster: Das Fenster.
    """
    verbindung = fenster.db  # type: ignore[attr-defined]
    dateien.kunde_speichern(verbindung, {"firma": "Tonstudio Nordwind"})
    dateien.kunde_speichern(verbindung, {"firma": "Zeta Tonwerk"})

    seite = _kunden(fenster)
    assert seite.modell.rowCount() == 2

    _waehle(seite, 0, "Zeta Tonwerk")
    seite.aktionen.stilllegen()

    assert seite.modell.rowCount() == 1, "Der stillgelegte Kunde ist noch da"
    assert len(dateien.kunden(verbindung)) == 2, "Er wurde wirklich geloescht"
    assert len(dateien.kunden(verbindung, nur_aktive=True)) == 1

    # Und mit dem Haken kommt er wieder.
    seite.zeige_auch_archiv = True
    seite.erneut_laden()
    assert seite.modell.rowCount() == 2, "Der stillgelegte Kunde ist nicht sichtbar"


def test_und_wieder_zurueck(fenster: object) -> None:
    """Ein stillgelegter Kunde kommt wieder in die Liste.

    Args:
        fenster: Das Fenster.
    """
    verbindung = fenster.db  # type: ignore[attr-defined]
    kennung = dateien.kunde_speichern(verbindung, {"firma": "Zeta Tonwerk"})

    dateien.kunde_stilllegen(verbindung, kennung, False)
    assert len(dateien.kunden(verbindung, nur_aktive=True)) == 0

    dateien.kunde_stilllegen(verbindung, kennung, True)
    assert len(dateien.kunden(verbindung, nur_aktive=True)) == 1


def test_ein_stillgelegter_kunde_laesst_sich_still_legen_ohne_tabelle(
    fenster: object,
) -> None:
    """Ein erfundener Tabellenname wird abgelehnt, nicht ausgeführt.

    Args:
        fenster: Das Fenster.
    """
    verbindung = fenster.db  # type: ignore[attr-defined]

    with pytest.raises(ValueError, match="Unbekannte Tabelle"):
        dateien._aktiv_setzen(verbindung, "kunden; DROP TABLE kunden", 1, False)


# ------------------------------------------------------------ Die vier Aktionen


def test_anlegen_legt_einen_kunden_an(
    fenster: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Der Weg über das Blatt landet in der Datenbank.

    Args:
        fenster: Das Fenster.
        monkeypatch: Zum Annehmen des Blattes.
    """
    verbindung = fenster.db  # type: ignore[attr-defined]
    seite = _kunden(fenster)

    from faktur.gui.formular import Formular

    monkeypatch.setattr(Formular, "exec", lambda self: Formular.DialogCode.Accepted)
    monkeypatch.setattr(
        Formular, "werte", lambda self: {"firma": "Soundcheck GmbH", "ort": "Hamburg"}
    )

    seite.aktionen.neu()

    angelegt = dateien.kunden(verbindung)
    assert [k["firma"] for k in angelegt] == ["Soundcheck GmbH"]
    assert seite.modell.rowCount() == 1


def test_aendern_schreibt_in_denselben_kunden(
    fenster: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kein zweter Kunde, sondern derselbe mit neuem Namen.

    Args:
        fenster: Das Fenster.
        monkeypatch: Zum Annehmen des Blattes.
    """
    verbindung = fenster.db  # type: ignore[attr-defined]
    kennung = dateien.kunde_speichern(verbindung, {"firma": "Zeta Tonwerk"})
    dateien.kunde_speichern(verbindung, {"firma": "Alpha Klangstudio"})

    seite = _kunden(fenster)

    from faktur.gui.formular import Formular

    monkeypatch.setattr(Formular, "exec", lambda self: Formular.DialogCode.Accepted)
    monkeypatch.setattr(Formular, "werte", lambda self: {"firma": "Zeta Tonwerk GmbH"})

    _waehle(seite, 0, "Zeta Tonwerk")
    assert seite.gewaehlt()["id"] == kennung, "Es ist der falsche Kunde markiert"
    seite.aktionen.aendern()

    assert len(dateien.kunden(verbindung)) == 2, "Es wurde ein Kunde angelegt"
    geaendert = [k for k in dateien.kunden(verbindung) if k["id"] == kennung][0]
    assert geaendert["firma"] == "Zeta Tonwerk GmbH"


def test_loeschen_ohne_markierung_tut_nichts(fenster: object) -> None:
    """Ohne Markierung wird nichts gelöscht — auch nicht der erste.

    Args:
        fenster: Das Fenster.
    """
    verbindung = fenster.db  # type: ignore[attr-defined]
    dateien.kunde_speichern(verbindung, {"firma": "Zeta Tonwerk"})

    seite = _kunden(fenster)
    seite.ansicht.clearSelection()
    seite.ansicht.setCurrentIndex(seite.modell.index(-1, -1))

    assert seite.aktionen.loeschen() is False
    assert len(dateien.kunden(verbindung)) == 1, "Es wurde ohne Markierung geloescht"


def test_die_frage_beim_loeschen_zaehlt_die_dokumente(fenster: object) -> None:
    """Ein Kunde mit Belegen wird anders gefragt als einer ohne.

    Args:
        fenster: Das Fenster.
    """
    verbindung = fenster.db  # type: ignore[attr-defined]
    ruhig = dateien.kunde_speichern(verbindung, {"firma": "Zeta Tonwerk"})
    beschaeftigt = dateien.kunde_speichern(verbindung, {"firma": "Soundcheck GmbH"})
    dateien.dokument_speichern(
        verbindung,
        {
            "art": "rechnung",
            "nummer": "0001",
            "kunde_id": beschaeftigt,
            "datum": "2026-01-01",
        },
        [],
    )

    frage = fenster.seiten["kunden"].aktionen  # type: ignore[attr-defined]

    ruhiger = dateien.kunde_holen(verbindung, ruhig)
    beschaefter = dateien.kunde_holen(verbindung, beschaeftigt)

    assert frage.frage(ruhiger) == (
        "„Zeta Tonwerk“ löschen? Der Kunde hat keine Dokumente."
    )
    mit_dokumenten = frage.frage(beschaefter)
    assert "1 Dokumente" in mit_dokumenten
    assert "Stilllegen" in mit_dokumenten, (
        "Es wird nicht gesagt, dass Stilllegen die bessere Wahl waere."
    )


def test_loeschen_nimmt_die_dokumente_mit(
    fenster: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Der Kunde ist weg, und die Frage hat vorher gewarnt.

    Args:
        fenster: Das Fenster.
        monkeypatch: Zum Beantworten der Frage.
    """
    verbindung = fenster.db  # type: ignore[attr-defined]
    kennung = dateien.kunde_speichern(verbindung, {"firma": "Zeta Tonwerk"})
    dateien.dokument_speichern(
        verbindung,
        {
            "art": "rechnung",
            "nummer": "0001",
            "kunde_id": kennung,
            "datum": "2026-01-01",
        },
        [{"bezeichnung": "Ton", "menge": 1, "einheit": "Tag", "preis": 100}],
    )

    seite = _kunden(fenster)

    from faktur.gui.qt import QMessageBox

    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )

    _waehle(seite, 0, "Zeta Tonwerk")
    assert seite.gewaehlt()["id"] == kennung, "Es ist der falsche Kunde markiert"
    assert seite.aktionen.loeschen() is True

    assert dateien.kunden(verbindung) == []
    assert dateien.dokumente(verbindung) == [], "Die Dokumente sind noch da"


def test_und_ein_nein_behaelt_alles(
    fenster: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wer *Abbrechen* sagt, behält seinen Kunden.

    Args:
        fenster: Das Fenster.
        monkeypatch: Zum Beantworten der Frage.
    """
    verbindung = fenster.db  # type: ignore[attr-defined]
    dateien.kunde_speichern(verbindung, {"firma": "Zeta Tonwerk"})

    seite = _kunden(fenster)

    from faktur.gui.qt import QMessageBox

    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Cancel),
    )

    _waehle(seite, 0, "Zeta Tonwerk")
    assert seite.aktionen.loeschen() is False
    assert len(dateien.kunden(verbindung)) == 1


# ------------------------------------------------------------------ Leistungen


def test_ein_preis_wird_zur_zahl(fenster: object) -> None:
    """„1.234,50“ kommt als Zahl in der Datenbank an.

    Args:
        fenster: Das Fenster.
    """
    verbindung = fenster.db  # type: ignore[attr-defined]
    fenster.gehe("leistungen")  # type: ignore[attr-defined]
    seite = fenster.seite()  # type: ignore[attr-defined]

    seite.speichere_neu(
        {
            "bezeichnung": "Bildberichtung zweitaegig",
            "einheit": "Stueck",
            "preis": "1.234,50",
        }
    )

    gespeichert = [
        leistung
        for leistung in dateien.leistungen(verbindung)
        if leistung["bezeichnung"] == "Bildberichtung zweitaegig"
    ]
    assert gespeichert, "Die Leistung wurde nicht angelegt"
    assert gespeichert[0]["preis"] == 1234.50


def test_und_ein_leistungspreis_wird_nicht_zu_text(fenster: object) -> None:
    """Nach dem Speichern ist der Preis eine Zahl, kein Wort.

    Args:
        fenster: Das Fenster.
    """
    verbindung = fenster.db  # type: ignore[attr-defined]
    fenster.gehe("leistungen")  # type: ignore[attr-defined]
    seite = fenster.seite()  # type: ignore[attr-defined]

    seite.speichere_neu(
        {"bezeichnung": "Mischung", "einheit": "Stunde", "preis": "950"}
    )

    treffer = [
        eine
        for eine in dateien.leistungen(verbindung)
        if eine["bezeichnung"] == "Mischung"
    ]
    assert isinstance(treffer[0]["preis"], float)
    assert treffer[0]["preis"] == 950.0


# ------------------------------------------------------------- Die Aufteilung


def _zeilen_ohne_fenster(felder: tuple[object, ...]) -> list[tuple[str, ...]]:
    """Rechnet aus, welche Felder in welcher Zeile landen.

    Ohne Fenster, weil es hier nur um die Aufteilung geht. Das Blatt selbst
    braucht eine Anwendung, die Zeilenreihen nicht.

    Args:
        felder: Die Felder in der Reihenfolge des Blattes.

    Returns:
        Je Zeile die Schluessel der Felder darin.
    """
    pytest.importorskip("PySide6")

    from faktur.gui.formular import Formular

    blatt = Formular.__new__(Formular)
    blatt.felder = felder

    return tuple(
        tuple(feld.schluessel for feld in gruppe) for gruppe in blatt._gruppen()
    ) and [tuple(feld.schluessel for feld in gruppe) for gruppe in blatt._gruppen()]


def test_postleitzahl_und_ort_teilen_sich_eine_zeile() -> None:
    """Zwei schmale Felder hintereinander stehen nebeneinander.

    Args:
        None
    """
    from faktur.gui.aktionen import KUNDENFELDER

    zeilen = _zeilen_ohne_fenster(KUNDENFELDER)

    assert ("plz", "ort") in zeilen, f"PLZ und Ort stehen nicht zusammen: {zeilen}"


def test_und_zwei_schmale_mit_einem_breiten_dazwischen_nicht() -> None:
    """Ein breites Feld dazwischen trennt die schmalen.

    Sonst stuende die Postleitzahl plötzlich neben dem Notizfeld.

    Args:
        None
    """
    from faktur.gui.formular import PAAR, Feld

    zeilen = _zeilen_ohne_fenster(
        (
            Feld("a", "A", PAAR),
            Feld("breit", "Breit"),
            Feld("b", "B", PAAR),
        )
    )

    assert zeilen == [("a",), ("breit",), ("b",)], f"Falsch zusammengefasst: {zeilen}"


def test_ein_ungerades_schmales_feld_bleibt_fuer_sich() -> None:
    """Ein einzelnes schmales Feld bekommt eine eigene Zeile.

    Args:
        None
    """
    from faktur.gui.formular import PAAR, Feld

    zeilen = _zeilen_ohne_fenster(
        (Feld("a", "A", PAAR), Feld("b", "B", PAAR), Feld("c", "C", PAAR))
    )

    assert zeilen == [("a", "b"), ("c",)], f"Falsch zusammengefasst: {zeilen}"


def test_und_alle_felder_bleiben_vorhanden() -> None:
    """Die Aufteilung verliert kein Feld und setzt keines doppelt.

    Args:
        None
    """
    from faktur.gui.aktionen import KUNDENFELDER, LEISTUNGFELDER

    for felder in (KUNDENFELDER, LEISTUNGFELDER):
        zeilen = _zeilen_ohne_fenster(felder)
        alle = [schluessel for zeile in zeilen for schluessel in zeile]
        erwartet = [feld.schluessel for feld in felder]

        assert alle == erwartet, f"Felder verschoben: {alle} statt {erwartet}"
