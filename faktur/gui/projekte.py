"""Die Projekte, und die Belege daneben.

**Ein Projekt ist ein Kunde und eine Nummer.** Angebot 0199 und Rechnung
0199 sind ein Vorgang, nicht zwei — und genau das war vorher nirgends zu
sehen. Es gab eine Dokumentenliste, in der beide als zwei verschiedene
Sachen standen, und keine Stelle, an der man einen Kunden und seinen
Vorgang gemeinsam hätte sehen können.

Darum steht hier beides nebeneinander: **links die Projekte, rechts die
Belege.** Markiert man links ein Projekt, stehen rechts genau seine
Belege untereinander — Angebot zuerst, Rechnung danach, weil es so
herauskam. Markiert man nichts, stehen rechts alle Belege.

**Die Zahlen meinen nicht dasselbe.** *Summe* ist das, was berechnet
wurde, und wo noch nichts berechnet wurde, das Angebot. *Offen* ist der
Betrag, auf den noch Geld fehlt — und da zählt nur die Rechnung hinein,
denn ein Angebot schuldet niemandem etwas. Beide Zahlen falsch zu lesen
ist teurer, als sie wegzulassen.
"""

from __future__ import annotations

import sqlite3

from faktur import dateien, suchen
from faktur.gui.listen import dokument_zellen, kurz_datum, nach_zahl
from faktur.gui.qt import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QSplitter,
    Qt,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from faktur.gui.seite import Seite
from faktur.gui.tabelle import ZeilenModell

#: Die Spalten der Projektliste.
#:
#: **Vier, nicht sechs.** Links steht nicht mal die halbe Fensterbreite,
#: und mit sechs Spalten war der Kunde dort auf *Soundc…*
#: zusammengeschoben — und an einem abgeschnittenen Kunden erkennt man
#: den Vorgang nicht.
#:
#: Die Geldsummen stehen deshalb *rechts*, und zwar an jedem einzelnen
#: Beleg. Ein Projekt hat meist ein Angebot und eine Rechnung, und deren
#: Beträge stehen nebeneinander — genauer als eine Summe in der
#: Projektliste, und an keiner Stelle doppelt.
SPALTEN = ("Kunde", "Nr.", "vom", "Stand")


class ProjekteSeite(Seite):
    """Die Projektliste links und die Belege rechts.

    Attributes:
        projekte: Die Tabelle mit den Projekten.
        belege: Die Tabelle mit den Belegen des markierten Projekts.
        ueberschrift_belege: Der Satz über der Belegtabelle.
    """

    def __init__(self, db: sqlite3.Connection) -> None:
        """Baut die Seite mit ihren beiden Tabellen.

        Args:
            db: Die Datenbankverbindung.
        """
        super().__init__(db, "Projekte")
        self.geoeffnet: object | None = None
        self.begriff = ""
        self.projektliste: list[sqlite3.Row] = []
        self.belegliste: list[sqlite3.Row] = []

        # Steht nur da, solange es nichts zu zeigen gibt. Eine
        # Erklaerung, die auch dann steht, wenn alles klar ist, ist ein
        # Zeile, die den eigentlichen Inhalt nach unten drueckt.
        self._leer = QLabel(
            "Noch kein Projekt. Sobald du ein Angebot anlegst, steht es "
            "hier — und rechts daneben seine Rechnung, wenn sie kommt."
        )
        self._leer.setObjectName("zweit")
        self._leer.setWordWrap(True)
        self._leer.setVisible(False)
        self._koerper.addWidget(self._leer)

        self.projekte = _tabelle(ZeilenModell(SPALTEN, self.projekte_zellen))
        self.belege = _tabelle(
            ZeilenModell(
                ("Nummer", "Datum", "Kunde", "Art", "Summe", "Status"),
                dokument_zellen(db),
                {4: nach_zahl(4)},
            )
        )

        # Beide Haelften bekommen eine Ueberschrift, und zwar aus
        # demselben Grund: Ohne sie stehen die Tabellenkopfe versetzt
        # untereinander, und die Seite sieht nach zwei Programmteilen aus.
        self.ueberschrift_projekte = QLabel()
        self.ueberschrift_projekte.setObjectName("zweit")
        self.ueberschrift_belege = QLabel()
        self.ueberschrift_belege.setObjectName("zweit")

        links = QWidget()
        links_anordnung = QVBoxLayout(links)
        links_anordnung.setContentsMargins(0, 0, 0, 0)
        links_anordnung.setSpacing(8)
        links_anordnung.addWidget(self.ueberschrift_projekte)
        links_anordnung.addWidget(self.projekte, 1)

        rechts = QWidget()
        rechts_anordnung = QVBoxLayout(rechts)
        rechts_anordnung.setContentsMargins(0, 0, 0, 0)
        rechts_anordnung.setSpacing(8)
        rechts_anordnung.addWidget(self.ueberschrift_belege)
        rechts_anordnung.addWidget(self.belege, 1)

        self.trenner = QSplitter(Qt.Orientation.Horizontal)
        self.trenner.setChildrenCollapsible(False)
        self.trenner.setHandleWidth(1)
        self.trenner.addWidget(links)
        self.trenner.addWidget(rechts)
        # **Anteile, keine Pixel.** Feste Breiten passen in einem Fenster
        # und passen im nächsten nicht: Bei 1040 Pixeln bekamen beide
        # Haelften 520, und die Belegliste brauchte 560 — also stand
        # rechts eine Bildlaufleiste. Mit Anteilen bleibt das Verhaeltnis,
        # wie breit das Fenster auch ist.
        self.trenner.setStretchFactor(0, 36)
        self.trenner.setStretchFactor(1, 64)
        self.trenner.setSizes([370, 660])
        self._koerper.addWidget(self.trenner, 1)

        self.projekte.selectionModel().selectionChanged.connect(self._gewaehlt)
        self.belege.doubleClicked.connect(self._doppelt)

    # ------------------------------------------------------------------ Daten

    def lade(self) -> None:
        """Holt die Projekte neu und folgt der Markierung.

        Returns:
            Nichts.
        """
        self.projektliste = dateien.projekte(self.db)
        self.fuelle(self.begriff)

    def fuelle(self, begriff: str) -> None:
        """Füllt die Projektliste nach einem Begriff.

        **Gesucht wird in den Projekten, nicht in den Belegen.** Zwei
        Suchfelder für eine Seite wären eine Frage mehr, als man beantworten
        kann, wenn man nicht weiß, welches gemeint ist.

        Args:
            begriff: Was gesucht wird.

        Returns:
            Nichts.
        """
        zeilen = [self.projekte_zellen(p) for p in self.projektliste]
        sichtbare = suchen.sichtbar(self.projektliste, zeilen, begriff)
        self.projekte.model().setze([p for p, _z in sichtbare])
        self._spalten_messen()
        self._leer.setVisible(not self.projektliste)
        self.ueberschrift_projekte.setText(
            "Projekte" if not self.begriff else f"Projekte mit „{self.begriff}“"
        )

        self.suchzeile.zeige(
            len(sichtbare),
            len(self.projektliste),
            begriff,
            "Projekte",
            "Projekt",
        )
        self._belege_zeigen()

    def _belege_zeigen(self) -> None:
        """Zeigt die Belege des markierten Projekts — oder alle.

        Returns:
            Nichts.
        """
        projekt = self.projekt()
        if projekt is None:
            self.belegliste = dateien.dokumente(self.db)
            self.ueberschrift_belege.setText(f"Alle Belege — {len(self.belegliste)}")
        else:
            self.belegliste = dateien.projekt_belege(self.db, projekt)
            self.ueberschrift_belege.setText(
                f"Belege von Projekt {projekt['nummer']} ({projekt['firma']})"
            )
        self.belege.model().setze(self.belegliste)
        self._belege_messen()

    # ---------------------------------------------------------------- Auswahl

    def projekt(self) -> sqlite3.Row | None:
        """Gibt das markierte Projekt zurück.

        Returns:
            Das Projekt, oder ``None``, wenn nichts markiert ist.
        """
        return self.projekte.model().datensatz(self.projekte.currentIndex().row())

    def gewaehlt(self) -> sqlite3.Row | None:
        """Gibt den Beleg zurück, auf den es ankommt.

        **Auf dieser Seite ist das ein Beleg, nicht ein Projekt.** Das
        Fenster fragt ``gaewaehlt()``, wenn man einen Beleg anklickt oder
        ⌘O drückt — und zu öffnen ist ein Beleg. Die Projektliste links ist
        der Weg dorthin, nicht das Ziel. Ohne diese Methode fand das
        Fenster auf dieser Seite gar nichts und tat still nichts.

        Returns:
            Der Beleg rechts, oder ``None``, wenn keiner markiert ist.
        """
        return self.belege.model().datensatz(self.belege.currentIndex().row())

    def _gewaehlt(self, _auswahl: object, _vorher: object) -> None:
        """Folgt der Markierung mit den Belegen.

        Args:
            _auswahl: Die neue Auswahl.
            _vorher: Die alte Auswahl.

        Returns:
            Nichts.
        """
        self._belege_zeigen()

    def _doppelt(self, index: object) -> None:
        """Öffnet den Beleg, auf den geklickt wurde.

        Args:
            index: Die Zeile in der Belegtabelle.

        Returns:
            Nichts.
        """
        if index is None or not index.isValid() or self.geoeffnet is None:
            return
        self.belege.setCurrentIndex(index)
        self.geoeffnet()

    # ----------------------------------------------------------------- Optik

    def projekte_zellen(self, projekt: sqlite3.Row) -> list[str]:
        """Baut die Zeile eines Projekts.

        Args:
            projekt: Das Projekt aus der Datenbank.

        Returns:
            Die Zellen der Zeile.
        """
        return [
            str(projekt["firma"]),
            str(projekt["nummer"]),
            kurz_datum(projekt["datum"]),
            dateien.projektstand(projekt),
        ]

    def _spalten_messen(self) -> None:
        """Misst die Spalten der Projektliste.

        Der Kunde bekommt den Rest, weil er der Name ist, an dem man den
        Vorgang erkennt. Alles andere darf abschneiden.

        Returns:
            Nichts.
        """
        kopf = self.projekte.horizontalHeader()
        kopf.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        kopf.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

    def _belege_messen(self) -> None:
        """Misst die Spalten der Belegtabelle.

        Returns:
            Nichts.
        """
        kopf = self.belege.horizontalHeader()
        kopf.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        if self.belege.model().spalten:
            kopf.setSectionResizeMode(
                len(self.belege.model().spalten) - 1, QHeaderView.ResizeMode.Stretch
            )


def _tabelle(modell: ZeilenModell) -> QTableView:
    """Baut eine Tabelle in der Art, wie alle anderen aussehen.

    **Nicht :class:`~faktur.gui.seite.ListenSeite`.** Die dort geht davon
    aus, dass sie die ganze Seite ist — mit Titel, Suchfeld und Tasten.
    Hier steht sie neben einer zweiten Tabelle, und zwei Titel und zwei
    Suchfelder auf einer Seite wären mehr, als man auf einen Blick
    verarbeiten kann.

    Args:
        modell: Das Modell der Tabelle.

    Returns:
        Die Tabelle.
    """
    ansicht = QTableView()
    ansicht.setObjectName("tabelle")
    ansicht.setModel(modell)
    ansicht.setFrameShape(QTableView.Shape.NoFrame)
    ansicht.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    ansicht.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    ansicht.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    ansicht.setAlternatingRowColors(True)
    ansicht.setShowGrid(False)
    ansicht.verticalHeader().setVisible(False)
    ansicht.horizontalHeader().setStretchLastSection(False)
    ansicht.horizontalHeader().setHighlightSections(False)
    ansicht.horizontalHeader().setSectionsClickable(True)
    return ansicht


__all__ = ["SPALTEN", "ProjekteSeite"]
