#!/usr/bin/env python3
"""Geht den ganzen Weg durch das Fenster.

Nicht mit Tastendrücken wie früher — das ging nicht anders, weil eine
Terminaloberfläche nur auf Tasten reagiert. Qt kennt dasselbe
`QTest.keyClick`, und der Durchlauf prüft damit dieselben Wege.

    .venv/bin/python scripts/ablauf_pruefen.py

Kunde anlegen, suchen, sortieren, die Bereiche durchgehen. Was noch nicht
da ist, wird als *fehlt noch* gemeldet und nicht als Fehler — sonst wäre
jede unfertige Stufe rot, und man wüsste nicht, ob etwas kaputt ist oder
einfach noch nicht gebaut.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from faktur import db  # noqa: E402
from faktur.gui.fenster import BEREICHE, Fenster  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


class Protokoll:
    """Sammelt, was der Durchlauf gemacht hat.

    Attributes:
        schritte: Die Zeilen, eine je Prüfung.
        fehler: Wie viele Prüfungen schiefgegangen sind.
        offen: Wie viele Dinge noch nicht gebaut sind.
    """

    def __init__(self) -> None:
        """Legt das Protokoll an."""
        self.schritte: list[str] = []
        self.fehler = 0
        self.offen = 0

    def ok(self, was: str) -> None:
        """Merkt sich, dass etwas geklappt hat.

        Args:
            was: Was geklappt hat.

        Returns:
            Nichts.
        """
        self.schritte.append(f"  ok      {was}")

    def schlecht(self, was: str, warum: str) -> None:
        """Merkt sich, dass etwas nicht geklappt hat.

        Args:
            was: Was nicht geklappt hat.
            warum: Warum nicht.

        Returns:
            Nichts.
        """
        self.fehler += 1
        self.schritte.append(f"  FEHLER  {was} — {warum}")

    def noch_nicht(self, was: str) -> None:
        """Merkt sich, dass etwas noch nicht gebaut ist.

        Args:
            was: Was noch fehlt.

        Returns:
            Nichts.
        """
        self.offen += 1
        self.schritte.append(f"  fehlt   {was}")


def _datenbank(ordner: Path) -> object:
    """Legt eine Datenbank mit einem Kunden und einem Dokument an.

    Args:
        ordner: Das Verzeichnis fuer die Datei.

    Returns:
        Die offene Verbindung.
    """
    from faktur import dateien, einstellungen

    verbindung = db.verbinden(ordner / "ablauf.db")
    einstellungen.speichere(verbindung, "firma", "New Air Media Group")
    einstellungen.speichere(verbindung, "iban", "DE02 1203 0000 0000 2020 51")

    kunde = dateien.kunde_speichern(
        verbindung,
        {"firma": "Soundcheck GmbH", "ort": "Hamburg"},
    )
    dateien.kunde_speichern(verbindung, {"firma": "Zeta Tonwerk", "ort": "Berlin"})
    leistung = dateien.leistung_speichern(
        verbindung,
        {"bezeichnung": "Aufnahme Ton", "einheit": "Tag", "preis": "850"},
    )
    nummer = dateien.naechste_nummer(verbindung)
    dateien.dokument_speichern(
        verbindung,
        {
            "art": "rechnung",
            "nummer": nummer,
            "kunde_id": kunde,
            "datum": "2026-10-12",
            "faellig": "2026-10-26",
        },
        [
            {
                "leistung_id": leistung,
                "bezeichnung": "Aufnahme Ton",
                "menge": 2,
                "einheit": "Tag",
                "preis": 850,
            }
        ],
    )
    return verbindung


def durchlauf(fenster: Fenster, app: QApplication, protokoll: Protokoll) -> None:
    """Prüft das Fenster, Bereich für Bereich.

    Args:
        fenster: Das Fenster.
        app: Die Anwendung, damit Qt zwischen den Schritten rechnen kann.
        protokoll: Wohin die Ergebnisse kommen.

    Returns:
        Nichts.
    """
    for _schluessel, titel, _kuerzel in BEREICHE:
        fenster.gehe(_schluessel)
        app.processEvents()
        if fenster.buehne.currentIndex() != fenster.reihenfolge.index(_schluessel):
            protokoll.schlecht(f"Bereich {titel}", "wurde nicht gewechselt")
        else:
            protokoll.ok(f"Bereich {titel}")

    fenster.gehe("kunden")
    app.processEvents()
    seite = fenster.seite()

    vorher = seite.modell.rowCount()
    if vorher:
        protokoll.ok(f"Kundenliste zeigt {vorher} Zeilen")
    else:
        protokoll.schlecht("Kundenliste", "ist leer, obwohl ein Kunde da ist")

    # Suchen. Das Feld wird getippt, nicht gesetzt: der Weg durch
    # `textChanged` ist genau der, den ein Benutzer auslöst.
    QTest.keyClicks(seite.suchfeld, "sound")
    app.processEvents()
    gefunden = seite.modell.rowCount()
    if gefunden and gefunden < vorher:
        protokoll.ok(f"Suche fand {gefunden} von {vorher}")
    else:
        protokoll.schlecht(
            "Suche", f"fand {gefunden} von {vorher}, erwartet dazwischen"
        )

    # Der gekürzte Begriff trifft auch mitten im Wort.
    QTest.keyClicks(seite.suchfeld, "check")
    app.processEvents()
    if seite.modell.rowCount() == gefunden:
        protokoll.ok("Suche findet auch einen Teil des Namens")
    else:
        protokoll.schlecht("Suche", "findet keinen Namensbestandteil")

    QTest.keyClick(seite.suchfeld, Qt.Key.Key_Escape)
    app.processEvents()
    if seite.modell.rowCount() == vorher:
        protokoll.ok("Escape leert das Suchfeld")
    else:
        protokoll.schlecht("Escape", "leert das Suchfeld nicht")

    # Sortieren. Nach dem Sortieren muss der Datensatz zur Zeile gehören,
    # in der er angezeigt wird — genau der Fehler aus 0.8.1.
    seite.modell.sortiere(0, False)
    app.processEvents()
    stimmig = True
    for zeile in range(seite.modell.rowCount()):
        angezeigt = seite.modell.waert(zeile, 0)
        dahinter = seite.modell.datensatz(zeile)
        if dahinter is None or dahinter["firma"] != angezeigt:
            stimmig = False
            protokoll.schlecht(
                "Sortieren",
                f"Zeile {zeile} zeigt „{angezeigt}“, "
                f"dahinter steht „{dahinter['firma'] if dahinter else 'nichts'}“",
            )
            break
    if stimmig:
        protokoll.ok("Nach dem Sortieren passt jede Zeile zu ihrem Datensatz")

    fenster.gehe("dokumente")
    app.processEvents()
    dokumente = fenster.seite()
    if dokumente.modell.rowCount():
        protokoll.ok(f"Dokumentenliste zeigt {dokumente.modell.rowCount()} Zeilen")
    else:
        protokoll.schlecht("Dokumentenliste", "ist leer, obwohl ein Beleg da ist")

    fenster.gehe("offen")
    app.processEvents()
    offene = fenster.seite()
    if offene.modell.rowCount():
        protokoll.ok(f"Offene Forderungen zeigt {offene.modell.rowCount()} Zeilen")
    else:
        protokoll.schlecht(
            "Offene Forderungen", "ist leer, obwohl eine Rechnung offen ist"
        )

    # Noch nicht gebaut. Das ist kein Fehler, sondern der Stand.
    for _schluessel, titel, _kuerzel in BEREICHE:
        if not hasattr(fenster.seiten[_schluessel], "modell"):
            protokoll.noch_nicht(f"Bereich {titel} hat noch keinen Inhalt")
    _formular_pruefen(fenster, app, protokoll)
    protokoll.noch_nicht("Dokumenteditor als eigenes Fenster")
    protokoll.noch_nicht("Einstellungen, Export und Übersicht")


def _formular_pruefen(
    fenster: Fenster, app: QApplication, protokoll: Protokoll
) -> None:
    """Legt einen Kunden an, ändert ihn, legt ihn still und holt ihn zurück.

    Die Fragen werden beantwortet wie am Bildschirm: das Blatt wird
    ausgefüllt, die Rückfrage mit *Ja* bestätigt.

    Args:
        fenster: Das Fenster.
        app: Die Anwendung, damit Qt zwischen den Schritten rechnen kann.
        protokoll: Wohin die Ergebnisse kommen.

    Returns:
        Nichts.
    """
    from faktur import dateien
    from faktur.gui.aktionen import KundenAktionen
    from faktur.gui.formular import Formular
    from faktur.gui.qt import QMessageBox

    fenster.gehe("kunden")
    app.processEvents()
    seite = fenster.seite()
    vorher = seite.modell.rowCount()

    # 1. Anlegen. Das Blatt wird mit Werten gefuellt statt getippt.
    Formular.werte = lambda self: {  # noqa: E731
        "firma": "Bildberichtung GmbH",
        "ansprechpartner": "",
        "strasse": "",
        "plz": "",
        "ort": "Muenchen",
        "email": "",
        "telefon": "",
        "notiz": "",
    }
    Formular.exec = lambda self: Formular.DialogCode.Accepted  # noqa: E731
    QMessageBox.question = staticmethod(  # noqa: E731
        lambda *a, **k: QMessageBox.StandardButton.Yes
    )

    try:
        seite.aktionen.neu()
        app.processEvents()
        if seite.modell.rowCount() == vorher + 1:
            protokoll.ok("Kunde anlegen")
        else:
            protokoll.schlecht(
                "Kunde anlegen", f"{vorher} -> {seite.modell.rowCount()}"
            )

        # 2. Aendern. Der Kunde muss derselbe bleiben, nicht ein zweiter.
        gefunden = [
            zeile
            for zeile in range(seite.modell.rowCount())
            if seite.modell.waert(zeile, 0) == "Bildberichtung GmbH"
        ]
        if not gefunden:
            protokoll.schlecht(
                "Kunde aendern", "der neue Kunde steht nicht in der Liste"
            )
            return
        seite.ansicht.setCurrentIndex(seite.modell.index(gefunden[0], 0))
        Formular.werte = lambda self: (
            dict.fromkeys(  # noqa: E731
                (
                    "firma",
                    "ansprechpartner",
                    "strasse",
                    "plz",
                    "ort",
                    "email",
                    "telefon",
                    "notiz",
                ),
                "",
            )
            | {"firma": "Bildberichtung AG"}
        )
        anzahl_vorher = len(dateien.kunden(fenster.db))
        seite.aktionen.aendern()
        app.processEvents()
        anzahl_nachher = len(dateien.kunden(fenster.db))
        if anzahl_vorher == anzahl_nachher and "Bildberichtung AG" in [
            k["firma"] for k in dateien.kunden(fenster.db)
        ]:
            protokoll.ok("Kunde aendern, ohne einen zweiten anzulegen")
        else:
            protokoll.schlecht(
                "Kunde aendern",
                f"{anzahl_vorher} Kunden vor, {anzahl_nachher} danach",
            )

        # 3. Stilllegen. Der Kunde verschwindet aus der Liste, nicht aus
        #    der Datenbank — und kommt ueber den Haken wieder.
        gefunden = [
            zeile
            for zeile in range(seite.modell.rowCount())
            if seite.modell.waert(zeile, 0) == "Bildberichtung AG"
        ]
        if not gefunden:
            protokoll.schlecht(
                "Stilllegen", "der geaenderte Kunde steht nicht in der Liste"
            )
            return
        seite.ansicht.setCurrentIndex(seite.modell.index(gefunden[0], 0))
        mit_dem = seite.modell.rowCount()
        seite.aktionen.stilllegen()
        app.processEvents()

        if seite.modell.rowCount() == mit_dem - 1:
            protokoll.ok("Stilllegen nimmt ihn aus der Liste")
        else:
            protokoll.schlecht(
                "Stilllegen", f"{mit_dem} -> {seite.modell.rowCount()} Zeilen"
            )

        if len(dateien.kunden(fenster.db)) == mit_dem:
            protokoll.ok("Der stillgelegte Kunde ist in der Datenbank geblieben")
        else:
            protokoll.schlecht(
                "Stilllegen", "der Kunde wurde geloescht statt stillgelegt"
            )

        # Steht er nicht mehr drin, war das stilllegen. Steht er noch da,
        # hat es den falschen Kunden erwischt.
        gefunden = [
            zeile
            for zeile in range(seite.modell.rowCount())
            if seite.modell.waert(zeile, 0) == "Bildberichtung AG"
        ]
        if gefunden:
            protokoll.schlecht(
                "Stilllegen",
                "er steht noch in der Liste — es wurde der falsche Kunde stillgelegt",
            )
            return

        # Er ist draussen. Jetzt ueber den Haken wieder herein und zurueck.
        seite.zeige_auch_archiv_setzen(True)
        app.processEvents()
        gefunden = [
            zeile
            for zeile in range(seite.modell.rowCount())
            if seite.modell.waert(zeile, 0) == "Bildberichtung AG"
        ]
        if not gefunden:
            protokoll.schlecht(
                "Haken", "der stillgelegte Kunde kommt mit „auch stillgelegte“ nicht"
            )
            return
        seite.ansicht.setCurrentIndex(seite.modell.index(gefunden[0], 0))
        kennung = seite.gewaehlt()["id"]
        seite.aktionen.stilllegen()
        app.processEvents()

        # Zaehlt nicht die Zeilen: Mit dem Haken stehen ohnehin alle da.
        # Zaehlt, was in der Datenbank steht.
        if dateien.kunde_holen(fenster.db, kennung)["aktiv"]:
            protokoll.ok("Stilllegen rueckgaengig, er ist wieder aktiv")
        else:
            protokoll.schlecht(
                "Stilllegen rueckgaengig", "er ist weiterhin stillgelegt"
            )

        seite.zeige_auch_archiv_setzen(False)
        app.processEvents()
        gefunden = [
            zeile
            for zeile in range(seite.modell.rowCount())
            if seite.modell.waert(zeile, 0) == "Bildberichtung AG"
        ]
        if gefunden:
            protokoll.ok("und ohne den Haken wieder in der normalen Liste")
        else:
            protokoll.schlecht(
                "Stilllegen rueckgaengig", "er fehlt auch ohne den Haken"
            )

        # 4. Loeschen. Ohne Markierung wird nichts geloescht.
        seite.ansicht.clearSelection()
        seite.ansicht.setCurrentIndex(seite.modell.index(-1, -1))
        vorher = len(dateien.kunden(fenster.db))
        if (
            seite.aktionen.loeschen() is False
            and len(dateien.kunden(fenster.db)) == vorher
        ):
            protokoll.ok("Loeschen ohne Markierung tut nichts")
        else:
            protokoll.schlecht("Loeschen", "hat ohne Markierung geloescht")

        del KundenAktionen
    finally:
        import faktur.gui.formular as formular_modul

        formular_modul.Formular.werte = Formular.werte
        del formular_modul


def main() -> int:
    """Fährt den Durchlauf und gibt das Ergebnis zurück.

    Returns:
        ``0``, wenn kein Schritt gescheitert ist.
    """
    ordner = Path(tempfile.mkdtemp(prefix="faktur_ablauf_"))
    app = QApplication.instance() or QApplication(sys.argv)

    verbindung = _datenbank(ordner)
    fenster = Fenster(verbindung)
    fenster.zeige()
    app.processEvents()

    protokoll = Protokoll()
    durchlauf(fenster, app, protokoll)

    fenster.fenster.close()
    shutil.rmtree(ordner, ignore_errors=True)

    print("Ablauf durch das Fenster")  # noqa: T201
    for zeile in protokoll.schritte:
        print(zeile)  # noqa: T201
    print()  # noqa: T201
    print(  # noqa: T201
        f"{len(protokoll.schritte) - protokoll.fehler - protokoll.offen} geklappt, "
        f"{protokoll.fehler} Fehler, {protokoll.offen} noch nicht gebaut"
    )
    return 1 if protokoll.fehler else 0


if __name__ == "__main__":
    raise SystemExit(main())
