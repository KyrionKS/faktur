"""Das Dokumentfenster, von aussen gesehen.

Diese Datei prüft, was ein Benutzer im Fenster erreicht: ein Angebot
bauen, es speichern, die PDF schreiben, ein Angebot abrechnen.

**Und sie prüft den Fehler aus 0.8.1 ein zweites Mal**, diesmal in der
gestalteten Form: Wenn die Positionenliste und die Angezeige auseinander
laufen, dann stimmt die PDF nicht mehr zum Bildschirm. Wer drei Positionen
sieht, muss drei Positionen bekommen.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

from faktur import betraege, dateien, db  # noqa: E402
from faktur.gui.editor import EditorFenster  # noqa: E402


@pytest.fixture
def app() -> object:
    """Gibt die laufende Qt-Anwendung zurück.

    Returns:
        Die Anwendung.
    """
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def verbindung(tmp_path: Path) -> sqlite3.Connection:
    """Legt eine frische Datenbank mit einem Kunden an.

    Args:
        tmp_path: Das temporäre Verzeichnis.

    Returns:
        Die offene Verbindung.
    """
    test = db.verbinden(tmp_path / "editor.db")
    dateien.kunde_speichern(test, {"firma": "Tonstudio Nordwind", "ort": "Hamburg"})
    dateien.kunde_speichern(test, {"firma": "Zeta Tonwerk", "ort": "Berlin"})
    return test


def _waehle_kunde(fenster: EditorFenster, firma: str = "Tonstudio Nordwind") -> None:
    """Wählt einen Kunden aus der Liste.

    Args:
        fenster: Das Dokumentfenster.
        firma: Der Name des Kunden.

    Returns:
        Nichts.
    """

    for nummer in range(fenster.kunde.count()):
        if fenster.kunde.itemText(nummer) == firma:
            fenster.kunde.setCurrentIndex(nummer)
            return
    raise AssertionError(f"{firma} steht nicht in der Kundenauswahl")


# ------------------------------------------------------------- Das Angebot


def test_ein_angebot_bauen_und_speichern(
    app: object, verbindung: sqlite3.Connection
) -> None:
    """Vom leeren Fenster zur Rechnung in der Datenbank.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
    """
    fenster = EditorFenster(verbindung)
    assert fenster.art.currentData() == "angebot", "Es beginnt nicht bei einem Angebot"
    assert fenster.frist_beschriftung.text() == "Gültig bis"

    _waehle_kunde(fenster)
    leistung = dateien.leistungen(verbindung)[0]
    fenster.positionen.aus_leistung(leistung)
    fenster.positionen.aus_leistung(leistung)

    assert fenster.speichern(mit_pdf=False) is True

    dokumente = dateien.dokumente(verbindung)
    assert len(dokumente) == 1
    assert dokumente[0]["art"] == "angebot"
    assert dokumente[0]["gueltig_bis"], "Das Ablaufdatum fehlt"
    assert len(dateien.positionen(verbindung, dokumente[0]["id"])) == 2


def test_und_die_summe_steht_gross_und_richtig_darunter(
    app: object, verbindung: sqlite3.Connection
) -> None:
    """Unter der Tabelle steht dieselbe Zahl wie in der Datenbank.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
    """
    fenster = EditorFenster(verbindung)
    _waehle_kunde(fenster)
    leistung = dateien.leistungen(verbindung)[0]
    fenster.positionen.aus_leistung(leistung)
    fenster.positionen.aus_leistung(leistung)

    erwartet = leistung["preis"] * 2
    assert fenster.positionen.summe() == pytest.approx(erwartet)
    assert betraege.euro(erwartet) in fenster.summe_label.text(), (
        f"Unter der Tabelle steht „{fenster.summe_label.text()}“, "
        f"erwartet wird {betraege.euro(erwartet)}."
    )

    fenster.speichern(mit_pdf=False)
    kennung = dateien.dokumente(verbindung)[0]["id"]
    assert dateien.summe_von(verbindung, kennung) == pytest.approx(erwartet)


def test_und_was_man_sieht_ist_auch_das_was_gespeichert_wird(
    app: object, verbindung: sqlite3.Connection
) -> None:
    """Drei Positionen im Bild, drei Positionen in der Datenbank.

    Genau das war der Fehler aus 0.8.1 in anderer Gestalt: Anzeige und
    Daten laufen auseinander, und am Ende stimmt die Rechnung nicht.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
    """
    fenster = EditorFenster(verbindung)
    _waehle_kunde(fenster)
    for _ in range(3):
        fenster.positionen.aus_leistung(dateien.leistungen(verbindung)[0])

    sichtbar = [
        fenster.positionen.data(fenster.positionen.index(zeile, 0), 0)
        for zeile in range(fenster.ansicht.model().rowCount())
    ]
    fenster.speichern(mit_pdf=False)

    kennung = dateien.dokumente(verbindung)[0]["id"]
    gespeichert = [
        str(p["bezeichnung"]) for p in dateien.positionen(verbindung, kennung)
    ]

    assert len(sichtbar) == 3
    assert gespeichert == sichtbar, (
        f"Im Bild stehen {sichtbar}, gespeichert wurde {gespeichert}."
    )


# --------------------------------------------------------------- Die Regeln


def test_ohne_kunde_wird_nicht_gespeichert(
    app: object, verbindung: sqlite3.Connection
) -> None:
    """Ein Beleg ohne Kunde ist kein Beleg.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
    """
    fenster = EditorFenster(verbindung)
    fenster.positionen.aus_leistung(dateien.leistungen(verbindung)[0])

    assert fenster.speichern(mit_pdf=False) is False
    assert dateien.dokumente(verbindung) == []


def test_und_ohne_positionen_auch_nicht(
    app: object, verbindung: sqlite3.Connection
) -> None:
    """Ein leerer Beleg geht nicht raus.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
    """
    fenster = EditorFenster(verbindung)
    _waehle_kunde(fenster)

    assert fenster.speichern(mit_pdf=False) is False
    assert dateien.dokumente(verbindung) == []


def test_und_ohne_nummer_auch_nicht(
    app: object, verbindung: sqlite3.Connection
) -> None:
    """Die Projektnummer gehört dazu.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
    """
    fenster = EditorFenster(verbindung)
    _waehle_kunde(fenster)
    fenster.positionen.aus_leistung(dateien.leistungen(verbindung)[0])
    fenster.nummer.setText("")

    assert fenster.speichern(mit_pdf=False) is False


def test_und_ein_unlesbares_datum_auch_nicht(
    app: object, verbindung: sqlite3.Connection
) -> None:
    """ "gestern" ist kein Datum.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
    """
    fenster = EditorFenster(verbindung)
    _waehle_kunde(fenster)
    fenster.positionen.aus_leistung(dateien.leistungen(verbindung)[0])
    fenster.datum.setText("gestern")

    assert fenster.speichern(mit_pdf=False) is False
    assert dateien.dokumente(verbindung) == []


def test_und_ein_unlesbares_datum_bleibt_lesbar_stehen(
    app: object, verbindung: sqlite3.Connection
) -> None:
    """Wer sich vertippt, soll es sehen und nicht verlieren.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
    """
    fenster = EditorFenster(verbindung)
    fenster.datum.setText("12.10.2026")

    assert fenster.kopf()["datum"] == "2026-10-12"


def test_die_art_wechselt_das_fristfeld(
    app: object, verbindung: sqlite3.Connection
) -> None:
    """Ein Angebot hat ein Ablaufdatum, eine Rechnung ein Fälligkeitsdatum.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
    """
    fenster = EditorFenster(verbindung)
    assert fenster.frist_beschriftung.text() == "Gültig bis"

    fenster.art.setCurrentIndex(1)
    assert fenster.art.currentData() == "rechnung"
    assert fenster.frist_beschriftung.text() == "Fällig am"
    assert fenster.frist.text(), "Es steht kein Fälligkeitsdatum"

    fenster.art.setCurrentIndex(0)
    assert fenster.frist_beschriftung.text() == "Gültig bis"


def test_und_die_frist_landet_im_richtigen_feld(
    app: object, verbindung: sqlite3.Connection
) -> None:
    """Bei einem Angebot nach ``gueltig_bis``, bei einer Rechnung nach ``faellig``.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
    """
    fenster = EditorFenster(verbindung)
    _waehle_kunde(fenster)
    fenster.positionen.aus_leistung(dateien.leistungen(verbindung)[0])
    fenster.art.setCurrentIndex(0)
    fenster.frist.setText("14.11.2026")

    assert fenster.kopf()["gueltig_bis"] == "2026-11-14"
    assert fenster.kopf()["faellig"] == ""

    fenster.art.setCurrentIndex(1)
    assert fenster.kopf()["faellig"] == "2026-11-14"
    assert fenster.kopf()["gueltig_bis"] == ""


# ------------------------------------------------------- Abrechnen und PDF


def test_aus_einem_angebot_wird_eine_rechnung_mit_gleicher_nummer(
    app: object, verbindung: sqlite3.Connection
) -> None:
    """Das Angebot und die Rechnung gehören zum selben Projekt.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
    """
    fenster = EditorFenster(verbindung)
    _waehle_kunde(fenster)
    leistung = dateien.leistungen(verbindung)[0]
    fenster.positionen.aus_leistung(leistung)
    fenster.speichern(mit_pdf=False)

    angebot = dateien.dokumente(verbindung)[0]

    fenster = EditorFenster(verbindung, angebots_id=angebot["id"])
    assert fenster.art.currentData() == "rechnung"
    assert fenster.nummer.text() == str(angebot["nummer"]), (
        "Die Projektnummer muss mitwandern — sonst wird aus einem Projekt ein zweites."
    )
    assert fenster.positionen.rowCount() == 1

    fenster.speichern(mit_pdf=False)
    rechnungen = [d for d in dateien.dokumente(verbindung) if d["art"] == "rechnung"]
    assert len(rechnungen) == 1
    assert rechnungen[0]["nummer"] == angebot["nummer"]


def test_und_die_positionen_wandern_mit(
    app: object, verbindung: sqlite3.Connection
) -> None:
    """Mengen und Preise bleiben, wie sie im Angebot standen.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
    """
    fenster = EditorFenster(verbindung)
    _waehle_kunde(fenster)
    leistung = dateien.leistungen(verbindung)[0]
    fenster.positionen.aus_leistung(leistung)
    fenster.positionen.aus_leistung(leistung)
    fenster.speichern(mit_pdf=False)
    angebot = dateien.dokumente(verbindung)[0]

    fenster = EditorFenster(verbindung, angebots_id=angebot["id"])

    assert fenster.positionen.summe() == pytest.approx(leistung["preis"] * 2)
    for position in fenster.positionen.positionen:
        assert position["leistung_id"] == leistung["id"], (
            "Ohne die Verknüpfung passt die Rechnung nicht wieder zur Preisliste."
        )


def test_speichern_und_pdf(
    app: object,
    verbindung: sqlite3.Connection,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Speichern mit PDF schreibt beides.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
        tmp_path: Das Verzeichnis fuer die PDF.
        monkeypatch: Zum Umleiten des Ausgabeordners.
    """
    ordner = tmp_path / "pdf"
    monkeypatch.setattr(db, "ausgabeordner", lambda: ordner)
    monkeypatch.setattr(db, "DOKUMENTE", ordner, raising=False)

    fenster = EditorFenster(verbindung)
    _waehle_kunde(fenster)
    fenster.positionen.aus_leistung(dateien.leistungen(verbindung)[0])

    from faktur.gui.qt import QMessageBox

    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: None))

    assert fenster.speichern(mit_pdf=True) is True

    geschrieben = sorted(ordner.glob("*.pdf"))
    assert len(geschrieben) == 1, f"Es liegen {len(geschrieben)} PDF im Ordner"
    assert geschrieben[0].stat().st_size > 1000, "Die PDF ist verdächtig klein"
    assert geschrieben[0].name.startswith("ANG - ")


def test_und_vor_dem_ueberschreiben_wird_gefragt(
    app: object,
    verbindung: sqlite3.Connection,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Liegt die PDF schon da, geht sie nicht ohne Frage weg.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
        tmp_path: Das Verzeichnis fuer die PDF.
        monkeypatch: Zum Umleiten und Antworten.
    """
    ordner = tmp_path / "pdf"
    ordner.mkdir()
    monkeypatch.setattr(db, "ausgabeordner", lambda: ordner)
    monkeypatch.setattr(db, "DOKUMENTE", ordner, raising=False)

    fenster = EditorFenster(verbindung)
    _waehle_kunde(fenster)
    fenster.positionen.aus_leistung(dateien.leistungen(verbindung)[0])
    fenster.speichern(mit_pdf=False)

    dokument = dateien.dokumente(verbindung)[0]
    ziel = ordner / f"{dateien.dateiname(dokument, 'angebot')}.pdf"
    ziel.write_bytes(b"die alte")

    from faktur.gui.qt import QMessageBox

    gefragt: list[str] = []
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(
            lambda *a, **k: (
                gefragt.append(" ".join(str(x) for x in a)),
                QMessageBox.StandardButton.Cancel,
            )[1]
        ),
    )

    assert fenster.speichern(mit_pdf=True) is False
    assert gefragt, "Es wurde nicht gefragt"
    assert ziel.read_bytes() == b"die alte", "Die alte PDF wurde ueberschrieben"
