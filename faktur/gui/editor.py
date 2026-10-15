"""Das Dokumentfenster.

**Ein Fenster, nicht ein Bildschirm im Programm.** Ein Angebot oder eine
Rechnung zu bauen ist eine eigene Aufgabe, und sie dauert: man schreibt
die Positionen, schiebt eine nach oben, korrigiert einen Preis. Wer dafür
durch eine Liste von Bildschirmen gehen muss, verliert den Faden.

Deshalb ist es ein eigenes Fenster. Man kann die Kundenliste daneben offen
lassen und nach einem Preis sehen, ohne das halbe Programm zu schließen.

**Die Positionen stehen in einer Tabelle.** Sie sind beschreibbar, sie
lassen sich verschieben, und die Summe steht darunter und rechnet bei jedem
Tastendruck mit. Umrechnen und Umstellen sind Wege aus dem Fenster heraus —
genau die Wege, die man nicht braucht.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from faktur import betraege, dateien, db, pdf, suchen
from faktur.gui.positionen import PositionenModell
from faktur.gui.qt import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSettings,
    Qt,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from faktur.gui.suchen import Suchfeld, SuchZeile

#: Die Arten, die es gibt.
ARTEN = (("angebot", "Angebot"), ("rechnung", "Rechnung"))


def _als_iso(text: str) -> str:
    """Macht aus einer Eingabe den Wert, wie er in der Datenbank steht.

    Args:
        text: Was getippt wurde, etwa ``12.10.2026``.

    Returns:
        Das Datum als ``2026-10-12``, oder ``""``, wenn es keines ist.
    """
    gefunden = betraege.lies_datum(text)
    return gefunden.isoformat() if gefunden else ""


def _als_text(wert: str) -> str:
    """Macht aus dem Datenbankwert etwas zum Lesen.

    Args:
        wert: Das Datum aus der Datenbank, oder ``""``.

    Returns:
        Das Datum als ``12.10.2026``, oder ``""``.
    """
    return betraege.datum(wert) if wert else ""


class LeistungsWaeler(QDialog):
    """Die Auswahl einer Leistung für eine Position.

    Attributes:
        gewaehlt: Die gewählte Leistung, oder ``None``.
    """

    def __init__(self, db: sqlite3.Connection, eltern: object = None) -> None:
        """Baut die Auswahl auf.

        Args:
            db: Die Datenbankverbindung.
            eltern: Das Fenster, zu dem die Auswahl gehört.
        """
        super().__init__(eltern)  # type: ignore[arg-type]
        self.db = db
        self.gewaehlt: sqlite3.Row | None = None
        self.setWindowTitle("Leistung wählen")
        self.setModal(True)
        self.resize(560, 460)

        self.alle = dateien.leistungen(db, nur_aktive=True)
        self.sichtbar = list(self.alle)

        self.suchfeld = Suchfeld(self._gesucht, "Leistung suchen")
        self.suchzeile = SuchZeile()
        self.suchzeile.setObjectName("suchzeile")

        self.liste = QTableView()
        self.liste.setObjectName("tabelle")
        self.liste.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.liste.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.liste.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.liste.verticalHeader().setVisible(False)
        self.liste.horizontalHeader().setStretchLastSection(True)

        self._fuellen()

        self.liste.doubleClicked.connect(self._genommen)
        self.liste.installEventFilter(self)

        knopf = QPushButton("Nehmen")
        knopf.setObjectName("haupt")
        knopf.clicked.connect(self._genommen)

        leiste = QHBoxLayout()
        leiste.addStretch(1)
        leiste.addWidget(knopf)

        anordnung = QVBoxLayout(self)
        anordnung.setContentsMargins(16, 16, 16, 16)
        anordnung.setSpacing(10)
        anordnung.addWidget(self.suchfeld)
        anordnung.addWidget(self.suchzeile)
        anordnung.addWidget(self.liste, 1)
        anordnung.addLayout(leiste)

        self.suchfeld.setFocus()

    # ------------------------------------------------------------- fuellen

    def _fuellen(self) -> None:
        """Zeichnet die Liste.

        Returns:
            Nichts.
        """
        from faktur.gui.tabelle import ZeilenModell, nach_zahl

        self.modell = ZeilenModell(
            ("Bezeichnung", "Einheit", "Preis"),
            lambda eine: [
                str(eine["bezeichnung"]),
                str(eine["einheit"] or ""),
                betraege.euro(eine["preis"]),
            ],
            {2: nach_zahl(2)},
        )
        self.modell.setze(self.sichtbar)
        self.liste.setModel(self.modell)
        kopf = self.liste.horizontalHeader()
        kopf.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        kopf.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.suchzeile.zeige(
            len(self.sichtbar),
            len(self.alle),
            self.suchfeld.text(),
            "Leistungen",
            "Leistung",
        )

    def _gesucht(self, begriff: str) -> None:
        """Sucht in der Preisliste.

        Args:
            begriff: Was getippt wurde.

        Returns:
            Nichts.
        """
        begriff = begriff.strip()

        # Ueber sichtbar(), nicht ueber passt(): Nur so bleibt Datensatz
        # und Zeile zusammen, und es gibt genau einen Filterweg im
        # ganzen Programm.
        paare = suchen.sichtbar(
            self.alle,
            [
                [str(leistung["bezeichnung"]), str(leistung["einheit"] or "")]
                for leistung in self.alle
            ],
            begriff,
        )
        self.sichtbar = [leistung for leistung, _zeile in paare]
        self._fuellen()

    # ---------------------------------------------------------- aktionen

    def _genommen(self) -> None:
        """Nimmt die markierte Leistung.

        Returns:
            Nichts.
        """
        datensatz = self.modell.datensatz(self.liste.currentIndex().row())
        if datensatz is None:
            self.suchzeile.setText("Erst eine Leistung markieren.")
            return
        self.gewaehlt = datensatz
        self.accept()

    def eventFilter(self, beobachter: object, ereignis: object) -> bool:  # noqa: N802
        """Macht aus der Eingabetaste ein *Nehmen*.

        Args:
            beobachter: Das beobachtete Objekt.
            ereignis: Das Ereignis.

        Returns:
            ``True``, wenn das Ereignis behandelt wurde.
        """
        from faktur.gui.qt import QKeyEvent

        if (
            isinstance(ereignis, QKeyEvent)
            and ereignis.key() == int(Qt.Key.Key_Return)
            and self.liste.hasFocus()
        ):
            self._genommen()
            return True
        return super().eventFilter(beobachter, ereignis)


class EditorFenster(QMainWindow):
    """Ein Angebot oder eine Rechnung, zum Schreiben.

    Attributes:
        db: Die Datenbankverbindung.
        dokument_id: Die Nummer des geöffneten Dokuments, oder ``None``.
        positionen: Das Modell der Positionen.
    """

    def __init__(
        self,
        db: sqlite3.Connection,
        dokument_id: int | None = None,
        angebots_id: int | None = None,
        eltern: object = None,
    ) -> None:
        """Baut das Fenster auf.

        Args:
            db: Die Datenbankverbindung.
            dokument_id: Ein Dokument, das geändert werden soll.
            angebots_id: Die Nummer eines Angebots, das abgerechnet wird.
            eltern: Das Hauptfenster.
        """
        super().__init__()
        self.db = db
        self.dokument_id = dokument_id

        # Dasselbe Verzeichnis wie das Hauptfenster, damit beide sich
        # dieselben Einstellungen teilen und nicht gegenseitig
        # ueberschreiben.
        self._einstellungen = QSettings("New Air Media Group", "Faktur")
        self.angebots_id = angebots_id
        self.positionen = PositionenModell(preise_genau=angebots_id is None)

        self.setWindowTitle(self._titel())
        self.resize(960, 720)

        zentrale = QWidget()
        anordnung = QVBoxLayout(zentrale)
        anordnung.setContentsMargins(20, 18, 20, 18)
        anordnung.setSpacing(14)
        anordnung.addWidget(self._kopf())
        anordnung.addWidget(self._tabelle(), 1)
        anordnung.addLayout(self._fuss())

        self.setCentralWidget(zentrale)
        self.statusBar().showMessage("Bereit")
        self._fuellen()

    # --------------------------------------------------------------- kopf

    def _titel(self) -> str:
        """Baut den Titel des Fensters.

        Returns:
            Der Titel.
        """
        if self.dokument_id is not None:
            dokument = dateien.dokument_holen(self.db, self.dokument_id)
            if dokument is not None:
                art = "Angebot" if dokument["art"] == "angebot" else "Rechnung"
                return f"{art} {dokument['nummer']}"
        return "Neue Rechnung" if self.angebots_id is not None else "Neues Angebot"

    def _kopf(self) -> QWidget:
        """Baut den Kopf mit allen Feldern.

        Returns:
            Das Widget.
        """
        kasten = QGroupBox("Kopfdaten")
        anordnung = QFormLayout(kasten)
        anordnung.setLabelAlignment(_rechts())
        anordnung.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        self.art = QComboBox()
        for wert, titel in ARTEN:
            self.art.addItem(titel, wert)
        self.art.currentIndexChanged.connect(self._art_gewechselt)
        anordnung.addRow("Art", self.art)

        self.nummer = QLineEdit()
        self.nummer.setToolTip(
            "Die Projektnummer. Angebot und Rechnung tragen dieselbe."
        )
        anordnung.addRow("Nummer", self.nummer)

        self.kunde = QComboBox()
        self.kunde.setEditable(True)
        self.kunde.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.kunde.setToolTip(
            "Tippen, um vorzusortieren. Der Name muss zum Kunden gehoeren, "
            "sonst steht er auf keinem Beleg."
        )
        self.kunde.activated.connect(self._kunde_gewahlt)
        anordnung.addRow("Kunde", self.kunde)

        self.datum = QLineEdit(betraege.heute())
        self.datum.setToolTip("Zum Beispiel 12.10.2026")
        anordnung.addRow("Datum", self.datum)

        self.frist = QLineEdit()
        self.frist.setToolTip("Zum Beispiel 26.10.2026")
        self.frist_beschriftung = QLabel("Fällig am")
        anordnung.addRow(self.frist_beschriftung, self.frist)

        self.notiz = QLineEdit()
        anordnung.addRow("Notiz", self.notiz)

        return kasten

    # ------------------------------------------------------------ tabelle

    def _tabelle(self) -> QWidget:
        """Baut die Positionstabelle mit ihren Tasten.

        Returns:
            Das Widget.
        """
        huelle = QWidget()
        anordnung = QVBoxLayout(huelle)
        anordnung.setContentsMargins(0, 0, 0, 0)
        anordnung.setSpacing(8)

        self.ansicht = QTableView()
        self.ansicht.setModel(self.positionen)
        self.ansicht.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.ansicht.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.ansicht.setAlternatingRowColors(True)
        self.ansicht.verticalHeader().setVisible(False)
        self.ansicht.setWordWrap(False)
        kopf = self.ansicht.horizontalHeader()
        kopf.setStretchLastSection(True)
        self.positionen.summen_geaendert.connect(self._summe_geaendert)

        knoepfe = QHBoxLayout()
        knoepfe.setSpacing(8)
        knoepfe.addWidget(self._knopf("Aus Leistung", self._aus_leistung))
        knoepfe.addWidget(self._knopf("Freie Position", self._freie_position))
        knoepfe.addStretch(1)
        knoepfe.addWidget(self._knopf("Nach oben", lambda: self._verschieben(-1)))
        knoepfe.addWidget(self._knopf("Nach unten", lambda: self._verschieben(1)))
        knoepfe.addWidget(self._knopf("Entfernen", self._entfernen))

        anordnung.addLayout(knoepfe)
        anordnung.addWidget(self.ansicht, 1)
        return huelle

    def _knopf(self, text: str, was: object) -> QPushButton:
        """Baut eine Taste.

        Args:
            text: Was drauf steht.
            was: Was sie tut.

        Returns:
            Die Taste.
        """
        taste = QPushButton(text)
        taste.clicked.connect(was)  # type: ignore[arg-type]
        return taste

    # --------------------------------------------------------------- fuss

    def _fuss(self) -> object:
        """Baut die Zeile mit der Summe und den Tasten.

        Returns:
            Das Layout.
        """
        self.summe_label = QLabel()
        self.summe_label.setObjectName("summe")
        anordnung = QHBoxLayout()
        anordnung.setSpacing(10)
        anordnung.addWidget(self.summe_label)
        anordnung.addStretch(1)

        self.zeile_ordner = QLabel()
        self.zeile_ordner.setObjectName("zweit")

        anordnung.addWidget(self.zeile_ordner)

        anordnung.addWidget(self._knopf("Speichern", self.speichern))
        # Das doppelte & ist ein echtes: Qt liest ein einfaches als
        # Tastenkuerzel und wuerde aus "& PDF" ein "_PDF" machen.
        pdf_erzeugen = self._knopf("PDF erzeugen && …", self.pdf_erzeugen)
        pdf_erzeugen.setObjectName("haupt")
        anordnung.addWidget(pdf_erzeugen)
        return anordnung

    # -------------------------------------------------------------- fuellen

    def _fuellen(self) -> None:
        """Trägt die vorhandenen Werte in die Felder.

        Returns:
            Nichts.
        """
        self.kunde.clear()
        self.kunde.addItem("", None)
        for kunde in dateien.kunden(self.db, nur_aktive=True):
            self.kunde.addItem(str(kunde["firma"]), kunde["id"])
        self.nummer.setText(dateien.naechste_nummer(self.db))

        dokument = None
        if self.dokument_id is not None:
            dokument = dateien.dokument_holen(self.db, self.dokument_id)

        if self.angebots_id is not None:
            self._setze_art("rechnung")
            if not self.aus_angebot(self.angebots_id):
                # Das Angebot laesst sich nicht abrechnen. Das Fenster
                # bleibt trotzdem offen und leer — jemand soll sehen, was
                # da ist, statt dass sich einfach nichts tut.
                self.nummer.setText("")
            return

        if dokument is None:
            self._setze_art("angebot")
            self._summe_geaendert()
            return

        self._setze_art(str(dokument["art"]))
        self.nummer.setText(str(dokument["nummer"]))
        self.datum.setText(_als_text(str(dokument["datum"])))
        self.notiz.setText(str(dokument["notiz"] or ""))
        self._setze_frist(
            str(dokument["faellig"] or ""), str(dokument["gueltig_bis"] or "")
        )

        self._waehle_kunde_nach(dokument["kunde_id"], str(dokument["firma"]))

        self.positionen.setze(
            [dict(p) for p in dateien.positionen(self.db, self.dokument_id)]
        )

    def _waehle_kunde_nach(self, kundennummer: object, name: str = "") -> None:
        """Markiert den Kunden mit dieser Nummer in der Auswahl.

        Args:
            kundennummer: Die Nummer des Kunden aus der Datenbank.
            name: Der Name, wie er im Feld stehen soll. Ohne Angabe
                bleibt der aus der Liste.

        Returns:
            Nichts.
        """
        for nummer in range(1, self.kunde.count()):
            if self.kunde.itemData(nummer) == kundennummer:
                self.kunde.setCurrentIndex(nummer)
                if name:
                    self.kunde.setEditText(name)
                return

    def _setze_art(self, art: str) -> None:
        """Stellt die Art ein und das Fristfeld daneben.

        Args:
            art: ``angebot`` oder ``rechnung``.

        Returns:
            Nichts.
        """
        for nummer, (wert, _titel) in enumerate(ARTEN):
            if wert == art:
                self.art.setCurrentIndex(nummer)
                break
        self._art_gewechselt()

    def _kunde_gewahlt(self, nummer: int) -> None:
        """Übernimmt den im Kundenfeld stehenden Namen.

        Wer statt aus der Liste zu tippen anfängt, könnte einen Namen
        eintragen, den es gar nicht gibt. Dann stünde auf dem Beleg ein
        Kunde ohne Datensatz — und die Rechnung wäre nicht zuzuordnen.

        Args:
            nummer: Die Nummer des Eintrags in der Liste.

        Returns:
            Nichts.
        """
        eintrag = self.kunde.item(nummer)
        if eintrag is None:
            return
        self.kunde.setEditText(eintrag.text())

    def _art_gewechselt(self) -> None:
        """Passt das Fristfeld an die Art an.

        Returns:
            Nichts.
        """
        rechnung = self.art.currentData() == "rechnung"
        self.frist_beschriftung.setText("Fällig am" if rechnung else "Gültig bis")

        # Nur vorschlagen, wenn noch nichts drinsteht. Sonst überschriebe
        # das Umschalten der Art ein Datum, das schon gesetzt war.
        if not self.frist.text().strip():
            self.frist.setText(betraege.plus_tage(14 if rechnung else 30))

    def _setze_frist(self, faellig: str, gueltig_bis: str) -> None:
        """Trägt das Fristdatum ein.

        Args:
            faellig: Das Fälligkeitsdatum aus der Datenbank.
            gueltig_bis: Das Ablaufdatum aus der Datenbank.

        Returns:
            Nichts.
        """
        self.frist.setText(_als_text(faellig or gueltig_bis))

    # ------------------------------------------------------------ summe

    def _summe_geaendert(self) -> None:
        """Schreibt die Summe unter die Tabelle.

        Returns:
            Nichts.
        """
        self.summe_label.setText(
            f"Gesamt {self.positionen.summe():,.2f} €".replace(",", "§")
            .replace(".", ",")
            .replace("§", ".")
        )

    # --------------------------------------------------------- positionen

    def _aus_leistung(self) -> None:
        """Holt eine Leistung aus der Preisliste.

        Returns:
            Nichts.
        """
        waehler = LeistungsWaeler(self.db, self)
        if waehler.exec() != QDialog.DialogCode.Accepted or waehler.gewaehlt is None:
            return
        self.positionen.aus_leistung(waehler.gewaehlt)
        self.ansicht.setCurrentIndex(
            self.positionen.index(self.positionen.rowCount() - 1, 0)
        )
        self.ansicht.edit(self.positionen.index(self.positionen.rowCount() - 1, 0))

    def _freie_position(self) -> None:
        """Setzt eine leere Position an.

        Returns:
            Nichts.
        """
        zeile = self.positionen.leere_zeile()
        self.ansicht.setCurrentIndex(self.positionen.index(zeile, 0))
        self.ansicht.edit(self.positionen.index(zeile, 0))

    def _verschieben(self, um: int) -> None:
        """Verschiebt die markierte Position.

        Args:
            um: ``-1`` nach oben, ``1`` nach unten.

        Returns:
            Nichts.
        """
        zeile = self.ansicht.currentIndex().row()
        if self.positionen.verschiebe(zeile, um):
            self.ansicht.setCurrentIndex(self.positionen.index(zeile + um, 0))

    def _entfernen(self) -> None:
        """Nimmt die markierte Position heraus.

        Returns:
            Nichts.
        """
        zeile = self.ansicht.currentIndex().row()
        if self.positionen.entferne(zeile):
            self.ansicht.setCurrentIndex(self.positionen.index(max(0, zeile - 1), 0))

    # -------------------------------------------------------------- inhalt

    def kopf(self) -> dict[str, str | int | None]:
        """Baut die Kopfdaten für :func:`faktur.dateien.dokument_speichern`.

        Returns:
            Die Kopfdaten.
        """
        return {
            "dokument_id": self.dokument_id,
            "art": str(self.art.currentData()),
            "nummer": self.nummer.text().strip(),
            "kunde_id": self.kunde.currentData(),
            "datum": _als_iso(self.datum.text()),
            "faellig": _als_iso(self.frist.text())
            if self.art.currentData() == "rechnung"
            else "",
            "gueltig_bis": _als_iso(self.frist.text())
            if self.art.currentData() == "angebot"
            else "",
            "notiz": self.notiz.text().strip(),
        }

    def _fragen(self) -> str:
        """Prüft die Eingaben und sagt, was fehlt.

        Returns:
            Der Text der Frage, oder ``""``, wenn alles da ist.
        """
        if not self.nummer.text().strip():
            return "Die Projektnummer fehlt."
        if not self.kunde.currentData():
            return "Es ist kein Kunde gewählt."
        if self.datum.text().strip() and not _als_iso(self.datum.text()):
            return "Das Datum ist nicht lesbar. Etwa so: 12.10.2026"
        if self.frist.text().strip() and not _als_iso(self.frist.text()):
            return "Das Fristdatum ist nicht lesbar. Etwa so: 26.10.2026"
        if not self.positionen.positionen:
            return "Das Dokument hat keine Position."
        for position in self.positionen.positionen:
            if not str(position.get("bezeichnung", "")).strip():
                return "Eine Position hat keine Bezeichnung."
        return ""

    # ------------------------------------------------------------ aktionen

    def melde(self, text: str) -> None:
        """Schreibt einen Satz in die Statuszeile dieses Fensters.

        Das Dokumentfenster hat seine eigene Leiste unten. Es könnte sich
        beim Hauptfenster melden — aber das kann auch geschlossen sein,
        während dieses Fenster offen bleibt.

        Args:
            text: Was geschehen ist.

        Returns:
            Nichts.
        """
        self.statusBar().showMessage(text)

    def speichern(self) -> bool:
        """Speichert das Dokument. Sonst nichts.

        Keine Frage, kein Fenster, kein Ordner. Wer nur speichern will,
        muss sich dafür nichts gefallen lassen.

        Returns:
            ``True``, wenn gespeichert wurde.
        """
        frage = self._fragen()
        if frage:
            QMessageBox.warning(self, "Nicht gespeichert", frage)
            return False

        kennung = dateien.dokument_speichern(
            self.db, self.kopf(), self.positionen.liste()
        )
        self.dokument_id = (
            kennung if self.dokument_id is None else int(self.dokument_id)
        )

        self.setWindowTitle(self._titel())
        self.melde("Gespeichert.")
        self.zeile_ordner.setText("")
        return True

    def pdf_erzeugen(self) -> bool:
        """Speichert das Dokument und fragt dann, wohin die PDF soll.

        **Erst speichern, dann fragen.** Sonst käme die PDF mit dem Stand
        von vor dem letzten Tippen heraus — ein Fehler, den man erst auf
        dem Papier merkt.

        Returns:
            ``True``, wenn die PDF geschrieben wurde.
        """
        if not self.speichern():
            return False

        dokument = dateien.dokument_holen(self.db, int(self.dokument_id or 0))
        if dokument is None:
            return False

        vorschlag = f"{dateien.dateiname(dokument, str(dokument['art']))}.pdf"
        ziel, _gefiltert = QFileDialog.getSaveFileName(
            self,
            "PDF speichern unter",
            str(self._ordner_vorschlag() / vorschlag),
            "PDF (*.pdf)",
        )
        if not ziel:
            # Abgebrochen. Der Beleg ist gespeichert, es gibt nur keine PDF.
            self.melde("Gespeichert, aber keine PDF geschrieben.")
            return False

        pfad = Path(ziel)
        if pfad.suffix.lower() != ".pdf":
            pfad = pfad.with_suffix(".pdf")

        try:
            pdf.erzeugen(self.db, dokument, pfad)
        except Exception as fehler:  # noqa: BLE001
            QMessageBox.critical(
                self,
                "PDF",
                f"Die PDF konnte nicht geschrieben werden:\n\n{fehler}",
            )
            return False

        self._ordner_merken(pfad.parent)
        self.zeile_ordner.setText(f"Geschrieben: {pfad}")
        self.melde(f"PDF geschrieben: {pfad.name}")
        return True

    def _ordner_vorschlag(self) -> Path:
        """Sagt, wo der Ordner zuletzt war.

        Beim ersten Mal der eigene Ordner des Programms. Er wird nicht
        mehr beschrieben, aber er ist ein vernünftiger Anfang, weil er
        schon existiert.

        Returns:
            Der Ordner, in dem der Dialog aufgeht.
        """
        gemerkt = self._einstellungen.value("pdf/ordner")
        if isinstance(gemerkt, str) and Path(gemerkt).is_dir():
            return Path(gemerkt)
        return db.ausgabeordner()

    def _ordner_merken(self, ordner: Path) -> None:
        """Merkt sich den Ordner für das nächste Mal.

        Args:
            ordner: Der Ordner, in den geschrieben wurde.

        Returns:
            Nichts.
        """
        self._einstellungen.setValue("pdf/ordner", str(ordner))

    def aus_angebot(self, dokument_id: int) -> bool:
        """Legt aus einem Angebot eine Rechnung an.

        Args:
            dokument_id: Die Nummer des Angebots.

        Returns:
            ``True``, wenn es geklappt hat.
        """
        try:
            kopf, positionen = dateien.als_angebot_uebernehmen(self.db, dokument_id)
        except ValueError as fehler:
            QMessageBox.warning(self, "Abrechnen", str(fehler))
            return False

        kopf.pop("dokument_id", None)
        kopf["datum"] = betraege.heute()
        kopf["faellig"] = _als_iso(betraege.plus_tage(14))
        self._setze_art("rechnung")
        self.nummer.setText(str(kopf.get("nummer", "")))
        self.datum.setText(_als_text(str(kopf.get("datum", ""))))
        self.frist.setText(_als_text(str(kopf.get("faellig", ""))))
        self.notiz.setText(str(kopf.get("notiz", "") or ""))
        self._waehle_kunde_nach(kopf.get("kunde_id"))

        self.positionen.setze(list(positionen))
        return True


def _rechts() -> object:
    """Gibt die Ausrichtung zurück, mit der Beschriftungen stehen.

    Returns:
        Die Ausrichtung.
    """
    return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


__all__ = ["ARTEN", "EditorFenster", "LeistungsWaeler"]
