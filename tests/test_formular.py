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
        "„Zeta Tonwerk“ löschen? Der Kunde hat keine Belege."
    )

    erlaubt, erklaerung = frage.darf_loeschen(beschaefter)
    assert erlaubt is False, "Ein Kunde mit Belegen darf geloescht werden"
    assert "1 Dokument" in erklaerung
    assert "Buchhaltung" in erklaerung


def test_ein_kunde_mit_belegen_wird_ueberhaupt_nicht_geloescht(
    fenster: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Statt *Löschen* gibt es nur noch *Stilllegen*.

    Das ist die eine Stelle im Programm, an der Daten unwiederbringlich
    weggehen könnten. Sie ist ab jetzt die einzige, an der es überhaupt
    eine Rückfrage gibt.

    Args:
        fenster: Das Fenster.
        monkeypatch: Zum Antworten im Dialog.
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

    angeboten: list[list[str]] = []

    def tu_exec(self: object) -> int:
        """Merkt sich, welche Tasten der Dialog anbietet.

        Args:
            self: Der Dialog.

        Returns:
            ``0``, wie bei ``exec()``.
        """
        angeboten.append([b.text() for b in self.buttons()])
        return 0

    monkeypatch.setattr(QMessageBox, "exec", tu_exec)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: None)

    _waehle(seite, 0, "Zeta Tonwerk")
    assert seite.aktionen.loeschen() is False, "Er wurde doch geloescht"

    assert angeboten, "Es wurde kein Dialog gezeigt"
    assert "Stilllegen" in angeboten[0], f"Der Dialog bietet nur {angeboten[0]}"
    assert "Löschen" not in angeboten[0], "Der Dialog bietet *Löschen* an"

    assert len(dateien.kunden(verbindung)) == 1, "Der Kunde wurde geloescht"
    assert dateien.kundenzahl(verbindung, kennung) == 1, "Die Belege sind weg"


def test_und_wer_stilllegt_kriegt_den_kunden_zurueck(
    fenster: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Der Dialog ist keine Sackgasse: *Stilllegen* geht auch.

    Args:
        fenster: Das Fenster.
        monkeypatch: Zum Antworten im Dialog.
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
        [],
    )

    seite = _kunden(fenster)

    from faktur.gui.qt import QMessageBox

    def tu_exec(self: object) -> int:
        """Drueckt auf *Stilllegen*, wie ein Benutzer.

        Args:
            self: Der Dialog.

        Returns:
            ``0``, wie bei ``exec()``.
        """
        for taste in self.buttons():
            if taste.text() == "Stilllegen":
                self.setDefaultButton(taste)
        return 0

    monkeypatch.setattr(QMessageBox, "exec", tu_exec)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: _erste_knopf(self))

    _waehle(seite, 0, "Zeta Tonwerk")
    seite.aktionen.loeschen()

    assert len(dateien.kunden(verbindung)) == 1, "Der Kunde wurde geloescht"
    assert dateien.kunden(verbindung, nur_aktive=True) == [], (
        "Der Kunde wurde nicht stillgelegt"
    )
    assert dateien.kundenzahl(verbindung, kennung) == 1


def _erste_knopf(dialog: object) -> object:
    """Gibt die erste Taste eines Dialogs zurück.

    Args:
        dialog: Der Dialog.

    Returns:
        Die erste Taste.
    """
    return dialog.buttons()[0]


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


# ------------------------------------------------------------- Doppelklick


def _hoert_aufs_blatt(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Lässt jeden Blattaufruf durchgehen und merkt sich den Titel.

    Args:
        monkeypatch: Zum Ersetzen von ``Formular.__init__``.

    Returns:
        Die Liste der Titel, in der Reihenfolge des Aufrufs.
    """
    from faktur.gui.formular import Formular

    titel: list[str] = []
    monkeypatch.setattr(
        Formular,
        "__init__",
        lambda self, db, fenstertitel, *a, **k: titel.append(fenstertitel),
    )
    monkeypatch.setattr(Formular, "exec", lambda self: Formular.DialogCode.Rejected)
    return titel


def test_doppelklick_oeffnet_das_blatt(
    fenster: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ein Doppelklick auf einen Kunden macht dasselbe wie *Ändern*.

    Das ist der Weg, den man in jedem anderen Programm erwartet. Er darf
    nicht erst gesucht werden müssen.

    **Das Signal wird geschickt, nicht geklickt.** ``QTest.mouseDClick``
    erzeugt ohne Bildschirm keinen Doppelklick — gemessen, nicht vermutet:
    die Ansicht bekommt das Ereignis nicht zu sehen. Der Slot und seine
    Verdrahtung sind das, was hier zu prüfen ist; die Mauseingabe muss man
    am Bildschirm prüfen, und dafür ist die Bedienung da.

    Args:
        fenster: Das Fenster.
        monkeypatch: Zum Aufzeichnen des Blattes.
    """
    verbindung = fenster.db  # type: ignore[attr-defined]
    dateien.kunde_speichern(verbindung, {"firma": "Zeta Tonwerk"})
    dateien.kunde_speichern(verbindung, {"firma": "Alpha Klangstudio"})

    seite = _kunden(fenster)
    titel = _hoert_aufs_blatt(monkeypatch)

    _waehle(seite, 0, "Zeta Tonwerk")
    seite.ansicht.doubleClicked.emit(
        seite.modell.index(seite.ansicht.currentIndex().row(), 0)
    )

    assert titel == ["Kunde ändern"], f"Der Doppelklick öffnete {titel}"


def test_und_derselbe_doppelklick_nimmt_den_markierten_kunden(
    fenster: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nach dem Sortieren meint der Doppelklick den, den man sieht.

    Das ist der ganze Sinn der Regel, dass Datensatz und Zeile zusammen im
    Modell liegen: Nach dem Sortieren muss der Doppelklick den **sichtbaren**
    Kunden treffen, nicht den, der vorher an dieser Stelle stand.

    Args:
        fenster: Das Fenster.
        monkeypatch: Zum Aufzeichnen, welches Blatt aufgeht.
    """
    verbindung = fenster.db  # type: ignore[attr-defined]
    dateien.kunde_speichern(verbindung, {"firma": "Zeta Tonwerk"})
    dateien.kunde_speichern(verbindung, {"firma": "Alpha Klangstudio"})

    seite = _kunden(fenster)

    from faktur.gui.formular import Formular

    geoeffnet: list[dict[str, str]] = []

    def tu_init(
        self: object, db: object, titel: str, felder: object, daten: dict, *a: object
    ) -> None:
        """Merkt sich, welche Werte in das Blatt kommen.

        Args:
            self: Das Blatt.
            db: Die Datenbankverbindung.
            titel: Der Titel.
            felder: Die Felder.
            daten: Die Werte des gewaehlten Kunden.
            a: Der Rest.

        Returns:
            Nichts.
        """
        geoeffnet.append(dict(daten))

    monkeypatch.setattr(Formular, "__init__", tu_init)
    monkeypatch.setattr(Formular, "exec", lambda self: Formular.DialogCode.Rejected)

    seite.modell.sortiere(0, False)
    _waehle(seite, 0, "Zeta Tonwerk")
    erwartet = seite.gewaehlt()["firma"]

    zeile = seite.ansicht.currentIndex().row()
    seite.ansicht.doubleClicked.emit(seite.modell.index(zeile, 0))

    assert geoeffnet, "Der Doppelklick hat nichts geoeffnet"
    assert geoeffnet[0]["firma"] == erwartet, (
        f"Der Doppelklick hat „{geoeffnet[0]['firma']}“ geoeffnet, "
        f"markiert war „{erwartet}“."
    )


def test_und_ein_doppelklick_neben_die_liste_oeffnet_nichts(
    fenster: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ein Doppelklick auf den leeren Raum daneben macht nichts.

    Args:
        fenster: Das Fenster.
        monkeypatch: Zum Aufzeichnen des Blattes.
    """
    verbindung = fenster.db  # type: ignore[attr-defined]
    dateien.kunde_speichern(verbindung, {"firma": "Zeta Tonwerk"})

    seite = _kunden(fenster)
    titel = _hoert_aufs_blatt(monkeypatch)

    # Ein Doppelklick neben der Liste trifft keine Zeile — und lässt die
    # Markierung trotzdem stehen, weil die sich nicht aufgehoben hat.
    seite.ansicht.doubleClicked.emit(seite.modell.index(-1, -1))

    assert titel == [], f"Der Doppelklick öffnete {titel}"


def test_und_ohne_markierung_oeffnet_der_doppelklick_auch_nichts(
    fenster: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ein Doppelklick ohne Auswahl hat keinen Kunden im Sinn.

    Args:
        fenster: Das Fenster.
        monkeypatch: Zum Aufzeichnen des Blattes.
    """
    verbindung = fenster.db  # type: ignore[attr-defined]
    dateien.kunde_speichern(verbindung, {"firma": "Zeta Tonwerk"})

    seite = _kunden(fenster)
    titel = _hoert_aufs_blatt(monkeypatch)

    seite.ansicht.clearSelection()
    seite.ansicht.setCurrentIndex(seite.modell.index(-1, -1))
    seite.ansicht.doubleClicked.emit(seite.modell.index(0, 0))

    assert titel == [], f"Der Doppelklick öffnete {titel}"


def test_das_gilt_auch_fuer_die_leistungen(
    fenster: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Eine Leistung laesst sich genauso oeffnen wie ein Kunde.

    Args:
        fenster: Das Fenster.
        monkeypatch: Zum Aufzeichnen des Blattes.
    """
    fenster.gehe("leistungen")  # type: ignore[attr-defined]
    seite = fenster.seite()  # type: ignore[attr-defined]
    titel = _hoert_aufs_blatt(monkeypatch)

    _waehle(seite, 0, "Aufnahme Ton")
    zeile = seite.ansicht.currentIndex().row()
    seite.ansicht.doubleClicked.emit(seite.modell.index(zeile, 0))

    assert titel == ["Leistung ändern"], f"Der Doppelklick öffnete {titel}"
