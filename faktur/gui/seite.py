"""Die Form jeder Seite.

**Ein Fenster, eine Seitenleiste, ein Bereich.** Jede Seite im Fenster hat
dieselbe Form: ein Titel, oben rechts die Tasten, darunter ein Suchfeld,
darunter die Liste. Wer das einmal gesehen hat, kennt alle sechs Bereiche.

Deshalb steht der Rahmen hier und nicht sechsmal im Programm. Eine Seite
sagt nur noch drei Dinge: **wie sie heißt**, **wie eine Zeile aussieht** und
**woher sie ihre Daten holt**. Wie viele Zeilen es sind, wie sie sortieren,
was beim Suchen übrig bleibt — das ist überall gleich und steht deshalb hier.
"""

from __future__ import annotations

import sqlite3

from faktur import suchen
from faktur.gui.qt import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from faktur.gui.suchen import Suchfeld, SuchZeile
from faktur.gui.tabelle import Eintrag, Vergleich, ZeilenModell, Zellen


class Seite(QWidget):
    """Eine Seite im Hauptfenster.

    Attributes:
        db: Die Datenbankverbindung.
        titel: Der Titel über der Liste.
    """

    def __init__(self, db: sqlite3.Connection, titel: str) -> None:
        """Baut das Gerüst der Seite.

        Args:
            db: Die Datenbankverbindung.
            titel: Der Titel über der Liste.
        """
        super().__init__()
        self.db = db
        self.titel = titel

        self.kopf = QHBoxLayout()
        self.kopf.setContentsMargins(0, 0, 0, 0)
        self.schrift = QLabel(f"<h2>{titel}</h2>")
        self.kopf.addWidget(self.schrift)
        self.kopf.addStretch(1)
        self.tasten = QHBoxLayout()
        self.tasten.setSpacing(8)
        self.kopf.addLayout(self.tasten)

        self.suchfeld = Suchfeld(self._gesucht)
        self.suchzeile = SuchZeile()
        self.suchzeile.setObjectName("suchzeile")

        anordnung = QVBoxLayout()
        anordnung.setContentsMargins(24, 20, 24, 16)
        anordnung.setSpacing(10)
        anordnung.addLayout(self.kopf)
        anordnung.addWidget(self.suchfeld)
        anordnung.addWidget(self.suchzeile)
        self.setLayout(anordnung)

        self._koerper = anordnung

    def knopf(
        self, text: str, was: object, kurz: str = "", spitz: bool = False
    ) -> QPushButton:
        """Setzt eine Taste neben den Titel.

        Args:
            text: Was auf der Taste steht.
            was: Wird gerufen, wenn die Taste gedrückt wird.
            kurz: Das Kürzel, das an der Taste steht, etwa ``⌘N``.
            spitz: Ob die Taste hervorgehoben wird, für die Hauptaktion.

        Returns:
            Die Taste.
        """
        beschriftung = f"{text}  {kurz}" if kurz else text
        taste = QPushButton(beschriftung)
        taste.setObjectName("haupt" if spitz else "normal")
        taste.clicked.connect(was)  # type: ignore[arg-type]
        self.tasten.addWidget(taste)
        return taste

    def ohne_suche(self) -> None:
        """Nimmt das Suchfeld weg.

        Für Seiten, die noch keinen Inhalt haben. Ein Feld, das nichts
        findet, ist schlimmer als keines: Man tippt hinein und weiß nicht,
        ob das Programm kaputt ist oder noch nicht fertig.

        Returns:
            Nichts.
        """
        self.suchfeld.setVisible(False)
        self.suchzeile.setVisible(False)

    def beim_zeigen(self) -> None:
        """Wird beim Wechsel auf die Seite gerufen.

        Returns:
            Nichts.
        """
        self.lade()

    def erneut_laden(self) -> None:
        """Lädt die Seite nach einer Änderung neu.

        Returns:
            Nichts.
        """
        self.lade()

    def lade(self) -> None:
        """Holt die Daten neu.

        Wird von :meth:`beim_zeigen` und :meth:`erneut_laden` gerufen.
        Unterklassen überschreiben das.

        Returns:
            Nichts.
        """

    def _gesucht(self, begriff: str) -> None:
        """Sucht weiter, während getippt wird.

        Args:
            begriff: Was getippt wurde.

        Returns:
            Nichts.
        """
        self.begriff = begriff.strip()
        self.fuelle(self.begriff)

    def fuelle(self, begriff: str) -> None:
        """Füllt die Liste nach einem Begriff.

        Unterklassen überschreiben das.

        Args:
            begriff: Was gesucht wird.

        Returns:
            Nichts.
        """


class ListenSeite(Seite):
    """Eine Seite mit einer Tabelle darin.

    Die Tabelle ist der eigentliche Inhalt. Das Suchfeld filtert sie, und
    weil Datensatz und Zeile zusammen im Modell liegen, kann ein Klick
    hinterher nicht auf etwas anderes zeigen als das, was man sieht.

    Attributes:
        modell: Das Modell der Tabelle.
        ansicht: Die Tabelle selbst.
        datensaetze: Alle Datensätze, ungefiltert.
        begriff: Was gerade gesucht wird.
        einheit: Die Pluralform für die Suchzeile, etwa *Kunden*.
    """

    def __init__(
        self,
        db: sqlite3.Connection,
        titel: str,
        spalten: tuple[str, ...],
        zellen: Zellen,
        einheit: str,
        einzeln: str,
        vergleiche: dict[int, Vergleich] | None = None,
        stretch_spalte: int = -1,
    ) -> None:
        """Baut die Seite und ihre Tabelle.

        Args:
            db: Die Datenbankverbindung.
            titel: Der Titel über der Liste.
            spalten: Die Spaltentitel.
            zellen: Baut aus einem Datensatz die Zellen.
            einheit: Die Pluralform für die Suchzeile.
            einzeln: Die Singularform für die Suchzeile.
            vergleiche: Je Spaltennummer eine eigene Vergleichsfunktion.
            stretch_spalte: Welche Spalte den Rest der Breite bekommt.
                ``-1`` heisst die letzte — meist die, die am wenigsten
                bedeutet und deshalb ruhig abschneiden darf.
        """
        super().__init__(db, titel)
        self.modell = ZeilenModell(spalten, zellen, vergleiche)
        self.einheit = einheit
        self.einzeln = einzeln
        self.stretch_spalte = stretch_spalte
        self.datensaetze: list[Eintrag] = []
        self.begriff = ""

        self.ansicht = QTableView()
        self.ansicht.setObjectName("tabelle")
        self.ansicht.setModel(self.modell)
        self.ansicht.setFrameShape(QTableView.Shape.NoFrame)
        self.ansicht.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.ansicht.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.ansicht.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ansicht.setAlternatingRowColors(True)
        self.ansicht.setShowGrid(False)
        self.ansicht.verticalHeader().setVisible(False)
        self.ansicht.horizontalHeader().setStretchLastSection(False)
        self.ansicht.horizontalHeader().setHighlightSections(False)
        self.ansicht.horizontalHeader().setSectionsClickable(True)

        self._koerper.addWidget(self.ansicht, 1)

    def lade(self) -> None:
        """Holt die Daten neu und filtert nach dem Begriff.

        Returns:
            Nichts.
        """
        self.datensaetze = self.hole()
        self.fuelle(self.begriff)

    def hole(self) -> list[Eintrag]:
        """Holt die Datensätze dieser Seite.

        Unterklassen überschreiben das.

        Returns:
            Die Datensätze in der Reihenfolge, in der sie erscheinen.
        """
        return []

    def fuelle(self, begriff: str) -> None:
        """Füllt die Tabelle nach einem Begriff.

        Gefiltert wird über :func:`faktur.suchen.sichtbar`, also über die
        Indizes und nicht über die Zellinhalte. Sonst könnten zwei Kunden
        mit gleichem Namen einen Rücksprung auf den falschen erlauben.

        Args:
            begriff: Was gesucht wird.

        Returns:
            Nichts.
        """
        zeilen = [self.modell.zellen(d) for d in self.datensaetze]
        sichtbare = suchen.sichtbar(self.datensaetze, zeilen, begriff)
        self.modell.setze([datensatz for datensatz, _zeile in sichtbare])
        self._spalten_messen()
        self.suchzeile.zeige(
            len(sichtbare),
            len(self.datensaetze),
            begriff,
            self.einheit,
            self.einzeln,
        )

    def _spalten_messen(self) -> None:
        """Misst die Spalten und lässt eine den Rest füllen.

        Ohne das bekommen alle Spalten dieselbe Breite, und der Name
        *Soundcheck GmbH* wird zu *Soundcheck ...* abgeschnitten — genau
        an der Stelle, an der man einen Kunden erkennt.

        Args:
            Keine.

        Returns:
            Nichts.
        """
        kopf = self.ansicht.horizontalHeader()
        kopf.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        if not self.modell.spalten:
            return
        breiteste = self.stretch_spalte
        if breiteste < 0:
            breiteste = len(self.modell.spalten) - 1
        kopf.setSectionResizeMode(breiteste, QHeaderView.ResizeMode.Stretch)

    def gewaehlt(self) -> Eintrag | None:
        """Gibt den Datensatz der markierten Zeile zurück.

        Returns:
            Der Datensatz, oder ``None``, wenn nichts markiert ist.
        """
        return self.modell.datensatz(self.ansicht.currentIndex().row())

    # ------------------------------------------------- haefft fuer Aktionen

    def melde(self, text: str) -> None:
        """Schreibt einen Satz in die Statuszeile des Fensters.

        Args:
            text: Was geschehen ist.

        Returns:
            Nichts.
        """
        fenster = self.window()
        while fenster is not None and not hasattr(fenster, "melde"):
            fenster = fenster.parent()
        if fenster is not None:
            fenster.melde(text)  # type: ignore[attr-defined]

    def unten_add(self, teil: object) -> None:
        """Setzt etwas unter die Liste.

        Args:
            teil: Das Widget, etwa einen Haken.

        Returns:
            Nichts.
        """
        self._koerper.addWidget(teil)  # type: ignore[arg-type]

    def zeige_auch_archiv_setzen(self, wert: bool) -> None:
        """Schaltet um, ob die stillgelegten Datensätze mitkommen.

        Args:
            wert: ``True`` zeigt sie mit.

        Returns:
            Nichts.
        """
        self.zeige_auch_archiv = wert
        self.erneut_laden()

    # ------------------------------------------- was die Seiten selbst tun

    def als_daten(self, datensatz: Eintrag) -> dict[str, str]:
        """Macht aus einem Datensatz die Werte für ein Formular.

        Args:
            datensatz: Der Datensatz aus der Datenbank.

        Returns:
            Die Werte, wie sie in der Datenbank heißen.
        """
        return {}

    def kennung(self, datensatz: Eintrag) -> int:
        """Gibt die Nummer eines Datensatzes zurück.

        Args:
            datensatz: Der Datensatz aus der Datenbank.

        Returns:
            Seine Nummer.
        """
        return 0

    def name(self, daten: dict[str, str]) -> str:
        """Gibt den Namen zurück, wie er in einer Frage steht.

        Args:
            daten: Die Werte des Datensatzes.

        Returns:
            Der Name.
        """
        return daten.get("firma") or daten.get("bezeichnung") or ""

    def speichere_neu(self, daten: dict[str, str]) -> None:
        """Legt einen neuen Datensatz an.

        Args:
            daten: Die Werte aus dem Formular.

        Returns:
            Nichts.
        """

    def speichere_alt(self, kennung: int, daten: dict[str, str]) -> None:
        """Ändert einen bestehenden Datensatz.

        Args:
            kennung: Seine Nummer.
            daten: Die Werte aus dem Formular.

        Returns:
            Nichts.
        """

    def loesche(self, kennung: int) -> None:
        """Löscht einen Datensatz.

        Args:
            kennung: Seine Nummer.

        Returns:
            Nichts.
        """

    def stilllege(self, kennung: int, aktiv: bool) -> None:
        """Legt einen Datensatz still oder holt ihn zurück.

        Args:
            kennung: Seine Nummer.
            aktiv: Ob er in den Listen stehen soll.

        Returns:
            Nichts.
        """
