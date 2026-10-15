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

    assert fenster.speichern() is True

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

    fenster.speichern()
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
    fenster.speichern()

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

    assert fenster.speichern() is False
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

    assert fenster.speichern() is False
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

    assert fenster.speichern() is False


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

    assert fenster.speichern() is False
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
    fenster.speichern()

    angebot = dateien.dokumente(verbindung)[0]

    fenster = EditorFenster(verbindung, angebots_id=angebot["id"])
    assert fenster.art.currentData() == "rechnung"
    assert fenster.nummer.text() == str(angebot["nummer"]), (
        "Die Projektnummer muss mitwandern — sonst wird aus einem Projekt ein zweites."
    )
    assert fenster.positionen.rowCount() == 1

    fenster.speichern()
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
    fenster.speichern()
    angebot = dateien.dokumente(verbindung)[0]

    fenster = EditorFenster(verbindung, angebots_id=angebot["id"])

    assert fenster.positionen.summe() == pytest.approx(leistung["preis"] * 2)
    for position in fenster.positionen.positionen:
        assert position["leistung_id"] == leistung["id"], (
            "Ohne die Verknüpfung passt die Rechnung nicht wieder zur Preisliste."
        )


# ----------------------------------------------------------- Die PDF erzeugen


def _bereit(
    verbindung: sqlite3.Connection,
) -> EditorFenster:
    """Baut ein Dokumentfenster, das gespeichert werden kann.

    Args:
        verbindung: Die Datenbankverbindung.

    Returns:
        Das Fenster.
    """
    fenster = EditorFenster(verbindung)
    _waehle_kunde(fenster)
    fenster.positionen.aus_leistung(dateien.leistungen(verbindung)[0])
    return fenster


def _zeige_auf(
    monkeypatch: pytest.MonkeyPatch, ordner: Path, antwort: str = ""
) -> list[str]:
    """Lässt den Speichern-Dialog auf einen Ordner zeigen.

    Args:
        monkeypatch: Zum Ersetzen des Dialogs.
        ordner: Wohin der Dialog zeigen soll.
        antwort: Der Dateiname, den der Dialog zurückgibt. Leer heißt
            *Abgebrochen*.

    Returns:
        Die Liste der angebotenen Startpfade.
    """
    from faktur.gui.qt import QFileDialog

    gesehen: list[str] = []

    def tu_get(
        eltern: object, titel: str, vorschlag: str, gefilter: str
    ) -> tuple[str, str]:
        """Tut so, als haette jemand einen Ordner gewaehlt.

        Args:
            eltern: Das Fenster.
            titel: Der Titel des Dialogs.
            vorschlag: Der Pfad, den der Dialog vorschlaegt.
            gefilter: Der Dateifilter.

        Returns:
            Der gewaehlte Pfad und der Filter.
        """
        gesehen.append(vorschlag)
        if not antwort:
            return "", ""
        # In den gewaehlten Ordner, nicht an den vom Programm vorgeschlagenen.
        # Sonst landet jede PDF im echten Datenordner des Benutzers — was
        # beim ersten Versuch dieses Tests tatsaechlich passiert ist.
        return str(ordner / antwort), gefilter

    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(tu_get))
    return gesehen


def test_die_pdf_lands_dort_wo_ich_sage(
    app: object,
    verbindung: sqlite3.Connection,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Der Dialog bestimmt den Ort, nicht das Programm.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
        tmp_path: Das Verzeichnis fuer die PDF.
        monkeypatch: Zum Ersetzen des Dialogs.
    """
    ordner = tmp_path / "wo auch immer"
    ordner.mkdir()
    fenster = _bereit(verbindung)
    _zeige_auf(monkeypatch, ordner, "meine Rechnung.pdf")

    assert fenster.pdf_erzeugen() is True

    geschrieben = ordner / "meine Rechnung.pdf"
    assert geschrieben.is_file(), "Die PDF liegt nicht dort, wo gewaehlt wurde"
    assert geschrieben.stat().st_size > 1000, "Die PDF ist verdächtig klein"


def test_und_der_name_ist_vorgefuellt(
    app: object,
    verbindung: sqlite3.Connection,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Im Dialog steht schon der richtige Name drin.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
        tmp_path: Das Verzeichnis fuer den Dialog.
        monkeypatch: Zum Ersetzen des Dialogs.
    """
    fenster = _bereit(verbindung)
    gesehen = _zeige_auf(monkeypatch, tmp_path, "x.pdf")

    fenster.pdf_erzeugen()

    assert gesehen, "Der Dialog wurde nie gezeigt"
    name = Path(gesehen[0]).name
    assert name.startswith("ANG - "), f"Der Name ist „{name}“"
    assert "Tonstudio Nordwind" in name
    assert name.endswith(".pdf")


def test_und_beim_abbrechen_bleibt_die_alte_stehen(
    app: object,
    verbindung: sqlite3.Connection,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wer abbricht, ueberschreibt nichts — der Beleg ist trotzdem gespeichert.

    Das ist der ganze Grund fuer die Frage: Es geht nicht darum, dass
    Faktur die Datei findet, sondern darum, dass niemand sie ungefragt
    verliert. Und der Beleg ist zu dem Zeitpunkt schon gespeichert —
    abbruchen heisst nur: keine PDF.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
        tmp_path: Das Verzeichnis fuer die PDF.
        monkeypatch: Zum Ersetzen des Dialogs.
    """
    ordner = tmp_path / "pdf"
    ordner.mkdir()
    alt = ordner / "ANG - 0001 - Tonstudio Nordwind.pdf"
    alt.write_bytes(b"die alte")

    fenster = _bereit(verbindung)
    _zeige_auf(monkeypatch, ordner)  # kein Name: abgebrochen

    assert fenster.pdf_erzeugen() is False
    assert alt.read_bytes() == b"die alte", "Die alte PDF wurde angefasst"
    assert not list(ordner.glob("x.pdf"))
    assert len(dateien.dokumente(verbindung)) == 1, (
        "Der Beleg wurde nicht gespeichert — abgebrochen heisst nur: keine PDF."
    )


def test_und_bei_einem_unvollstaendigen_beleg_fragt_gar_nicht(
    app: object,
    verbindung: sqlite3.Connection,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Erst wird gespeichert. Passt es nicht, kommt kein Ordnerfenster.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
        tmp_path: Das Verzeichnis fuer den Dialog.
        monkeypatch: Zum Ersetzen des Dialogs.
    """
    fenster = EditorFenster(verbindung)
    fenster.positionen.aus_leistung(dateien.leistungen(verbindung)[0])
    gesehen = _zeige_auf(monkeypatch, tmp_path, "x.pdf")

    assert fenster.pdf_erzeugen() is False
    assert gesehen == [], "Der Dialog wurde trotzdem gezeigt"


def test_und_der_letzte_ordner_steht_beim_naechsten_mal_da(
    app: object,
    verbindung: sqlite3.Connection,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ein zweites Mal fragt nicht wieder von ganz vorn.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
        tmp_path: Das Verzeichnis fuer die PDF.
        monkeypatch: Zum Ersetzen des Dialogs.
    """
    ordner = tmp_path / "Rechnungen 2026"
    ordner.mkdir()

    fenster = _bereit(verbindung)
    _zeige_auf(monkeypatch, ordner, "a.pdf")
    fenster.pdf_erzeugen()

    zweites = _bereit(verbindung)
    gesehen = _zeige_auf(monkeypatch, ordner, "b.pdf")
    zweites.pdf_erzeugen()

    assert str(ordner) in gesehen[0], f"Der Dialog nennt „{gesehen[0]}“"


def test_und_speichern_allein_fragt_nichts(
    app: object,
    verbindung: sqlite3.Connection,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wer nur speichern will, bekommt kein Fenster.

    Args:
        app: Die Qt-Anwendung.
        verbindung: Die Datenbankverbindung.
        tmp_path: Das Verzeichnis, das *nicht* benutzt werden darf.
        monkeypatch: Zum Aufzeichnen, ob ein Dialog kam.
    """
    fenster = _bereit(verbindung)
    gesehen = _zeige_auf(monkeypatch, tmp_path, "x.pdf")

    assert fenster.speichern() is True

    assert gesehen == [], "Beim Speichern wurde ein Dialog gezeigt"
    assert not list(tmp_path.glob("*.pdf")), "Es wurde eine PDF geschrieben"
    assert len(dateien.dokumente(verbindung)) == 1
