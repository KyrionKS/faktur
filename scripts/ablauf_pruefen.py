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

    _projekte_pruefen(fenster, app, protokoll)

    # Noch nicht gebaut. Das ist kein Fehler, sondern der Stand.
    #
    # **Nach dem Listenmodell fragen, nicht nach einer Tabelle.** Vorher
    # stand hier ``hasattr(seite, "modell")``, und die Projektseite hat aus
    # gutem Grund zwei Tabellen und damit kein einzelnes ``modell`` — sie
    # wurde dadurch fuer nicht gebaut gehalten und blieb auf der Liste
    # *fehlt*, obwohl sie fertig war.
    #
    # Nicht nach *irgendeiner* Tabelle fragen: Die Stammdatenseite hat in
    # den Brieftexten inzwischen selbst eine, und galt dadurch als fertig
    # — wodurch ihre Pruefung ersatzlos wegfiel.
    _stammdaten_pruefen(fenster, fenster.seiten["stammdaten"], protokoll)

    for _schluessel, titel, _kuerzel in BEREICHE:
        if _schluessel in _EIGENES_GEPRUEFT:
            continue
        if _hat_liste(fenster.seiten[_schluessel]):
            continue
        protokoll.noch_nicht(f"Bereich {titel} hat noch keinen Inhalt")
    _formular_pruefen(fenster, app, protokoll)
    _dokument_pruefen(fenster, app, protokoll)
    _uebersicht_pruefen(fenster, app, protokoll)
    protokoll.noch_nicht("Export fuer den Steuerberater")


#: Bereiche, die nicht ueber eine Listenpage laufen und deshalb eine
#: eigene Pruefung bekommen.
#:
#: **Ausdruecklich, nicht aus der Form geschlossen.** Uebersicht und
#: Stammdaten tragen beide eine Tabelle, aber keine Listenpage: die eine
#: zeigt Monatssummen, die andere Platzhalter. Vorher standen beide in der
#: Schleife ueber die *nicht gebauten* Bereiche, und die Uebersicht stand
#: dort, weil sie kein Listenmodell hat — obwohl sie fertig war.
_EIGENES_GEPRUEFT = frozenset({"stammdaten", "uebersicht"})


def _uebersicht_pruefen(fenster: Fenster, app: object, protokoll: Protokoll) -> None:
    """Prueft, dass auf der Uebersicht Zahlen stehen.

    Nicht, *welche* — das machen die Tests mit genauen Betraegen. Hier
    geht es um das grobe: Es steht etwas da, und es steht etwas da, das
    eine Zahl ist.

    Args:
        fenster: Das Fenster.
        app: Die Qt-Anwendung.
        protokoll: Wohin das Ergebnis kommt.

    Returns:
        Nichts.
    """
    fenster.gehe("uebersicht")
    app.processEvents()
    seite = fenster.seite()

    fehlen = [name for name, gross in seite._gross.items() if gross.text() == "—"]
    if fehlen:
        protokoll.schlecht("Uebersicht", f"laesst {fehlen} ohne Zahl")
        return
    protokoll.ok(f"Uebersicht zeigt {len(seite._gross)} Zahlen")

    if seite._monats_tabelle.rowCount():
        protokoll.ok(f"und {seite._monats_tabelle.rowCount()} Monate")
    else:
        protokoll.schlecht("Uebersicht", "zeigt keine Monate")


def _hat_liste(seite: object) -> bool:
    """Sagt, ob die Seite eine Liste von Datensaetzen zeigt.

    **Nach dem Modell, nicht nach dem Widget.** Jede Listenpage traegt ein
    :class:`~faktur.gui.tabelle.ZeilenModell`; die Stammdatenseite
    dagegen eine einfache Tabelle fuer die Platzhalter. Wer nur nach
    *einer* Tabelle fragt, haelt die Stammdatenseite fuer eine
    Listenpage — und prueft sie damit nicht mehr.

    Args:
        seite: Die Seite aus dem Fenster.

    Returns:
        ``True``, wenn die Seite eine Liste zeigt.
    """
    from faktur.gui.tabelle import ZeilenModell
    from PySide6.QtWidgets import QTableView

    return any(
        isinstance(ansicht.model(), ZeilenModell)
        for ansicht in seite.findChildren(QTableView)
    )


def _projekte_pruefen(fenster: Fenster, app: object, protokoll: Protokoll) -> None:
    """Prueft, dass ein Projekt seine Belege rechts zeigt.

    Das ist der ganze Sinn der Seite: Angebot und Rechnung eines Kunden
    als *ein* Vorgang. Steht links das Projekt und stehen nicht seine
    Belege rechts, ist die Seite nicht gebaut, gleichgueltig wie viele
    Zeilen sie hat.

    Args:
        fenster: Das Fenster.
        app: Die Qt-Anwendung.
        protokoll: Wohin das Ergebnis kommt.

    Returns:
        Nichts.
    """
    fenster.gehe("projekte")
    app.processEvents()
    seite = fenster.seite()

    if not seite.projekte.model().rowCount():
        protokoll.schlecht("Projektliste", "ist leer, obwohl ein Beleg da ist")
        return
    protokoll.ok(f"Projektliste zeigt {seite.projekte.model().rowCount()} Projekte")

    seite.projekte.setCurrentIndex(seite.projekte.model().index(0, 0))
    app.processEvents()

    if seite.belege.model().rowCount():
        protokoll.ok(
            f"und daneben {seite.belege.model().rowCount()} Belege desselben Projekts"
        )
    else:
        protokoll.schlecht("Belegliste", "zeigt nichts zum markierten Projekt")

    # Ohne Markierung muessen wieder *alle* Belege stehen, nicht die des
    # markierten Projekts. Sonst waere die rechte Liste eine Falle: man
    # glaubt, es gaebe nur diese Belege.
    alle = seite.belege.model().rowCount()
    seite.projekte.clearSelection()
    app.processEvents()
    if seite.belege.model().rowCount() == alle:
        protokoll.ok(f"ohne Markierung stehen wieder alle {alle} Belege da")
    else:
        protokoll.schlecht(
            "Belegliste",
            f"zeigt nach dem Abwaehlen {seite.belege.model().rowCount()} statt {alle}",
        )


def _dialoge_stumm() -> None:
    """Beantwortet jeden Dialog, ohne auf jemanden zu warten.

    ``QMessageBox.warning()`` und seine Geschwister halten den Ablauf an,
    bis ein Mensch klickt. Hier klickt niemand, also beantwortet diese
    Funktion alles selbst — *Abbrechen*, die vorsichtigste Antwort, die es
    gibt. Sie ist **nur** fuer diesen Durchlauf da; im Programm steht
    keine davon.

    Returns:
        Nichts.
    """
    from faktur.gui.qt import QMessageBox

    for name in ("exec", "warning", "critical", "information"):
        setattr(QMessageBox, name, staticmethod(lambda *a, **k: 0))
    QMessageBox.question = staticmethod(  # noqa: E731
        lambda *a, **k: QMessageBox.StandardButton.Cancel
    )


def _stammdaten_pruefen(fenster: Fenster, seite: object, protokoll: Protokoll) -> None:
    """Prueft den Weg von „fehlt" ueber „gefuellt" zurueck zu „da".

    Die Durchlaufdatenbank ist bereits vollstaendig. Genau deshalb wird
    hier die IBAN erst weggenommen: Sonst waere der Hinweis zu Recht weg,
    und es gaebe nichts zu pruefen. Ein Test, der die falsche Lage
    voraussetzt, meldet Erfolg, wenn alles stimmt — und Fehler, wenn
    alles richtig ist.

    Args:
        fenster: Das Fenster.
        seite: Die Stammdatenseite.
        protokoll: Wohin die Ergebnisse kommen.

    Returns:
        Nichts.
    """
    from faktur import einstellungen

    # ``isHidden()`` und nicht ``isVisible()``: Die Seite steckt nicht
    # im gerade sichtbaren Stapel, und Qt meldet ein Widget dann als
    # unsichtbar, egal ob es eingeblendet wurde. Gemessen.
    uebersicht = fenster.seiten["uebersicht"]

    # 1. Die IBAN weg: Die Uebersicht muss warnen.
    einstellungen.speichere(fenster.db, "iban", "")
    uebersicht.beim_zeigen()
    if not uebersicht.hinweis.isHidden():
        protokoll.ok("die Uebersicht warnt bei fehlenden Stammdaten")
    else:
        protokoll.schlecht("Uebersicht", "sie warnt nicht, obwohl die IBAN fehlt")

    # 2. Von der Seite aus fuellen: Der Hinweis muss verschwinden.
    gespeicherte = einstellungen.hole(fenster.db, "iban")
    seite.felder["iban"].setText(gespeicherte or "DE02 1203 0000 0000 2020 51")
    if not einstellungen.hole(fenster.db, "firma"):
        seite.felder["firma"].setText("New Air Media Group")
    seite.speichern()

    if einstellungen.vollstaendig(fenster.db):
        protokoll.ok("Stammdaten speichern")
    else:
        protokoll.schlecht("Stammdaten", "sie wurden nicht gespeichert")

    uebersicht.beim_zeigen()
    if uebersicht.hinweis.isHidden():
        protokoll.ok("und der Hinweis verschwindet danach")
        protokoll.ok("und der Hinweis verschwindet danach")
    else:
        protokoll.schlecht("Uebersicht", "der Hinweis bleibt stehen")

    # 3. Und wieder loeschen: Er muss wiederkommen.
    einstellungen.speichere(fenster.db, "iban", "")
    uebersicht.beim_zeigen()
    if not uebersicht.hinweis.isHidden():
        protokoll.ok("und er kommt wieder, wenn etwas fehlt")
        protokoll.ok("und er kommt wieder, wenn etwas fehlt")
    else:
        protokoll.schlecht("Uebersicht", "der Hinweis kommt nicht wieder")


def _dokument_pruefen(
    fenster: Fenster, app: QApplication, protokoll: Protokoll
) -> None:
    """Baut ein Angebot, speichert es und rechnet es ab.

    **Mit eigener Datenbank.** Sonst zaehlt hier die Rechnung aus dem
    Kundenteil mit, und jede Zaehlung haengt daran, was vorher passiert
    ist. Das war nicht eine theoretische Sorge: die erste Fassung kam
    nicht durch, weil die Durchlaufdatenbank schon Belege hatte.

    Args:
        fenster: Das Fenster.
        app: Die Anwendung.
        protokoll: Wohin die Ergebnisse kommen.

    Returns:
        Nichts.
    """
    import shutil
    import tempfile

    from faktur import dateien
    from faktur import db as db_modul
    from faktur.gui.editor import EditorFenster

    frisch = Path(tempfile.mkdtemp(prefix="faktur_dokument_"))
    verbindung = db_modul.verbinden(frisch / "dokument.db")
    dateien.kunde_speichern(verbindung, {"firma": "Soundcheck GmbH"})
    dateien.kunde_speichern(verbindung, {"firma": "Zeta Tonwerk"})
    leistungen = dateien.leistungen(verbindung)

    try:
        editor = EditorFenster(verbindung)
        if editor.art.currentData() != "angebot":
            protokoll.schlecht("Editor", "ein neues Dokument ist kein Angebot")
            return
        protokoll.ok("Ein neues Fenster beginnt als Angebot")

        editor.positionen.aus_leistung(leistungen[0])
        editor.positionen.aus_leistung(leistungen[1])
        erwartet = float(leistungen[0]["preis"]) + float(leistungen[1]["preis"])
        if abs(editor.positionen.summe() - erwartet) > 0.005:
            protokoll.schlecht("Summe", f"{editor.positionen.summe()} statt {erwartet}")
        else:
            protokoll.ok("Summe unter der Tabelle rechnet mit")

        vorher = editor.positionen.summe()
        editor.positionen.verschiebe(1, -1)
        if editor.positionen.summe() == vorher:
            protokoll.ok("Umstellen aendert die Summe nicht")
        else:
            protokoll.schlecht("Umstellen", "hat die Summe veraendert")

        anzahl = len(dateien.dokumente(verbindung))
        if editor.speichern() is False and len(dateien.dokumente(verbindung)) == anzahl:
            protokoll.ok("ohne Kunde wird nicht gespeichert")
        else:
            protokoll.schlecht("Editor", "hat ohne Kunde gespeichert")
            return

        if not _waehle_kunde(editor, "Soundcheck GmbH"):
            protokoll.schlecht("Editor", "Soundcheck GmbH steht nicht in der Auswahl")
            return
        if editor.speichern():
            protokoll.ok("Angebot speichern")
        else:
            protokoll.schlecht("Editor", "das Angebot liess sich nicht speichern")
            return

        angebote = [d for d in dateien.dokumente(verbindung) if d["art"] == "angebot"]
        if len(angebote) != 1:
            protokoll.schlecht("Angebot", f"{len(angebote)} Angebote, 1 erwartet")
            return
        angebot = angebote[0]

        if (
            len(dateien.positionen(verbindung, angebot["id"]))
            == editor.positionen.rowCount()
        ):
            protokoll.ok("so viele Positionen in der Datenbank wie im Bild")
        else:
            protokoll.schlecht(
                "Angebot",
                f"{len(dateien.positionen(verbindung, angebot['id']))} in der "
                f"Datenbank, {editor.positionen.rowCount()} im Bild",
            )

        rechnung = EditorFenster(verbindung, angebots_id=angebot["id"])
        app.processEvents()

        if rechnung.art.currentData() != "rechnung":
            protokoll.schlecht("Abrechnen", "es wurde keine Rechnung daraus")
            return
        if rechnung.nummer.text() != str(angebot["nummer"]):
            protokoll.schlecht(
                "Abrechnen",
                f"Nummer {rechnung.nummer.text()} statt {angebot['nummer']}",
            )
            return
        if rechnung.positionen.rowCount() != 2:
            protokoll.schlecht("Abrechnen", "die Positionen sind nicht mitgewandert")
            return
        protokoll.ok("Aus dem Angebot wird eine Rechnung mit derselben Nummer")

        if rechnung.speichern():
            protokoll.ok("und die Rechnung liegt in der Datenbank")
        else:
            protokoll.schlecht("Abrechnen", "die Rechnung liess sich nicht speichern")

        editor.close()
        rechnung.close()
    finally:
        verbindung.close()
        shutil.rmtree(frisch, ignore_errors=True)


def _belege_anlegen(fenster: Fenster, kunde: int) -> None:
    """Haengt einen Beleg an einen Kunden.

    Args:
        fenster: Das Fenster.
        kunde: Die Nummer des Kunden.

    Returns:
        Nichts.
    """
    from faktur import dateien

    dateien.dokument_speichern(
        fenster.db,
        {
            "art": "rechnung",
            "nummer": dateien.naechste_nummer(fenster.db),
            "kunde_id": kunde,
            "datum": "2026-10-01",
            "faellig": "2026-10-15",
        },
        [
            {
                "bezeichnung": "Aufnahme Ton",
                "menge": 1,
                "einheit": "Tag",
                "preis": 850,
            }
        ],
    )


def _waehle_kunde(editor: object, firma: str) -> bool:
    """Waehlt einen Kunden im Dokumentfenster nach Namen.

    **Nach Namen, nicht nach Nummer.** Die Kundenauswahl hat vorn einen
    leeren Platz, ihre Nummern laufen also gegenueber der Datenbank um
    eins. Wer sie vergleicht, waehlt den leeren Platz und speichert
    nichts.

    Args:
        editor: Das Dokumentfenster.
        firma: Der Name des Kunden.

    Returns:
        ``True``, wenn der Kunde gefunden wurde.
    """
    for nummer in range(editor.kunde.count()):
        if editor.kunde.itemText(nummer) == firma:
            editor.kunde.setCurrentIndex(nummer)
            return True
    return False


def _waehle(seite: object, spalte: int, gesucht: str) -> object:
    """Markiert die Zeile, die in einer Spalte etwas Bestimmtes zeigt.

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
    raise AssertionError(f'"{gesucht}" steht nicht in der Liste')


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

    # Hier wird jeder Frage zugestimmt, weil sonst nichts geloescht
    # wuerde und der Durchlauf an dieser Stelle nichts pruefte.
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
        # 4b. Doppelklick. Er muss dasselbe tun wie *Aendern* — auch und
        #     gerade nach dem Sortieren, wo sich die Reihenfolge bewegt hat.
        geoeffnet: list[dict[str, str]] = []

        def merke_doppelklick(
            self: object,
            db: object,
            titel: str,
            felder: object,
            daten: dict,
            *a: object,
        ) -> None:
            """Schreibt die Werte mit, die in das Blatt kommen.

            Args:
                self: Das Blatt.
                db: Die Datenbankfenster.db.
                titel: Der Titel.
                felder: Die Felder.
                daten: Die Werte des gewaehlten Kunden.
                a: Der Rest.

            Returns:
                Nichts.
            """
            geoeffnet.append(dict(daten))

        Formular.__init__ = merke_doppelklick  # type: ignore[method-assign]

        for richtung, wohin in ((True, "auf"), (False, "ab")):
            seite.modell.sortiere(0, richtung)
            _waehle(seite, 0, "Bildberichtung AG")
            erwartet = seite.gewaehlt()["firma"]
            geoeffnet.clear()
            zeile = seite.ansicht.currentIndex().row()
            seite.ansicht.doubleClicked.emit(seite.modell.index(zeile, 0))
            app.processEvents()

            if not geoeffnet:
                protokoll.schlecht(
                    "Doppelklick", f"hat nach dem Sortieren {wohin} nichts geoeffnet"
                )
            elif geoeffnet[0]["firma"] != erwartet:
                protokoll.schlecht(
                    "Doppelklick",
                    f"sieht „{erwartet}“, geoeffnet wurde „{geoeffnet[0]['firma']}“",
                )
            else:
                protokoll.ok(f"Doppelklick trifft den markierten Kunden ({wohin})")

        # Neben die Liste geklickt: darf nichts aufmachen.
        geoeffnet.clear()
        seite.ansicht.doubleClicked.emit(seite.modell.index(-1, -1))
        app.processEvents()
        if geoeffnet:
            protokoll.schlecht("Doppelklick", "daneben hat etwas aufgegangen")
        else:
            protokoll.ok("Doppelklick neben der Liste tut nichts")

        seite.ansicht.doubleClicked.connect(seite.aktionen._doppelt)
        del merke_doppelklick

        # 5. Ein Kunde mit Belegen wird nicht geloescht.
        ruhiger = [
            k for k in dateien.kunden(fenster.db) if k["firma"] == "Soundcheck GmbH"
        ]
        if not ruhiger:
            protokoll.schlecht("Loeschen", "Soundcheck GmbH fehlt")
            return
        if dateien.kundenzahl(fenster.db, ruhiger[0]["id"]) == 0:
            _belege_anlegen(fenster, ruhiger[0]["id"])

        _waehle(seite, 0, "Soundcheck GmbH")
        erlaubt, erklaerung = seite.aktionen.darf_loeschen(
            dateien.kunde_holen(fenster.db, ruhiger[0]["id"])
        )
        if erlaubt:
            protokoll.schlecht(
                "Loeschen", "ein Kunde mit Belegen darf geloescht werden"
            )
        else:
            protokoll.ok("ein Kunde mit Belegen wird nicht geloescht")
            if "Buchhaltung" in erklaerung:
                protokoll.ok("und die Frage sagt, warum")
            else:
                protokoll.schlecht("Loeschen", f"die Frage sagt nichts: {erklaerung}")

        vorher = len(dateien.kunden(fenster.db))
        belege = dateien.kundenzahl(fenster.db, ruhiger[0]["id"])
        if (
            seite.aktionen.loeschen() is False
            and len(dateien.kunden(fenster.db)) == vorher
            and dateien.kundenzahl(fenster.db, ruhiger[0]["id"]) == belege
        ):
            protokoll.ok("und die Belege sind noch da")
        else:
            protokoll.schlecht("Loeschen", "hat den Kunden mit Belegen doch geloescht")

        # 6. Ein Kunde ohne Belege laesst sich wirklich loeschen.
        ruhiger = [
            k for k in dateien.kunden(fenster.db) if k["firma"] == "Zeta Tonwerk"
        ]
        if not ruhiger:
            protokoll.schlecht("Loeschen", "Zeta Tonwerk fehlt")
            return
        _waehle(seite, 0, "Zeta Tonwerk")
        vorher = len(dateien.kunden(fenster.db))
        if (
            seite.aktionen.loeschen() is True
            and len(dateien.kunden(fenster.db)) == vorher - 1
        ):
            protokoll.ok("ein Kunde ohne Belege laesst sich loeschen")
        else:
            protokoll.schlecht(
                "Loeschen",
                f"{vorher} Kunden vor, {len(dateien.kunden(fenster.db))} danach",
            )

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

    _dialoge_stumm()

    protokoll = Protokoll()
    durchlauf(fenster, app, protokoll)

    fenster.fenster.close()

    # **Erst schliessen, dann loeschen.** Sonst haengt SQLite beim
    # Abbruch noch an der Datei, die es gerade nicht mehr gibt.
    verbindung.close()
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
