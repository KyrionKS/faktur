"""Das Hauptfenster.

Ein Fenster, eine Seitenleiste, ein Bereich. Das ist der Aufbau von Mail
und von Notizen, und er ist der Grund, warum sich Faktur auf dem Mac nativ
anfühlt: Es gibt keine Seitenstapel aus Terminalprogrammen mehr, sondern
einen Ort, an dem man sich umsieht.

**Die Seitenleiste steht links, nicht oben.** Der Grund ist nicht die
Schönheit, sondern die Gewohnheit: Man lernt einmal, wo *Kunden* steht,
und danach muss man nicht mehr suchen.

**Was hier nicht steht:** Keine Berechnung, kein Datenbankzugriff. Jede Seite
holt ihre Liste über :mod:`faktur.dateien` und gibt eine Markierung zurück.
Dadurch lässt sich jede Seite ohne Fenster prüfen.
"""

from __future__ import annotations

import sqlite3

from faktur import __version__
from faktur.gui.befehle import Befehle
from faktur.gui.listen import (
    DokumenteSeite,
    KundenSeite,
    LeistungenSeite,
    OffeneSeite,
)
from faktur.gui.projekte import ProjekteSeite
from faktur.gui.qt import (
    QAction,
    QActionGroup,
    QApplication,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QSettings,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    Qt,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from faktur.gui.seite import Seite
from faktur.gui.stammdaten import StammdatenSeite
from faktur.gui.uebersicht import UebersichtSeite

#: Die Bereiche der Seitenleiste in der Reihenfolge, in der sie stehen.
#:
#: Dritter Eintrag ist das Kürzel, mit dem man den Bereich direkt ansteuert.
BEREICHE: tuple[tuple[str, str, str], ...] = (
    ("uebersicht", "Übersicht", "Ctrl+1"),
    ("projekte", "Projekte", "Ctrl+2"),
    ("dokumente", "Dokumente", "Ctrl+3"),
    ("offen", "Offene Forderungen", "Ctrl+4"),
    ("kunden", "Kunden", "Ctrl+5"),
    ("leistungen", "Leistungen", "Ctrl+6"),
    ("stammdaten", "Stammdaten", "Ctrl+7"),
)


class Fenster:
    """Der Rahmen: Seitenleiste, Seiten, Menüs, Statuszeile.

    Attributes:
        db: Die Datenbankverbindung.
        fenster: Das Hauptfenster.
        leiste: Die Seitenleiste links.
        buehne: Der Stapel, in dem die Seiten liegen.
        seiten: Die Seiten, je Schlüssel aus :data:`BEREICHE`.
        reihenfolge: Die Schlüssel in der Reihenfolge der Seitenleiste.
        einstellungen: Wo sich das Fenster Größe und Lage merkt.
    """

    def __init__(self, verbindung: sqlite3.Connection) -> None:
        """Baut das Fenster auf.

        Args:
            verbindung: Die Datenbankverbindung.
        """
        self.db = verbindung
        self._app = QApplication.instance()

        self.fenster = QMainWindow()
        self.fenster.setObjectName("hauptfenster")
        self.fenster.setWindowTitle("Faktur")
        # Breiter als vorher: die Projektseite stellt zwei Tabellen
        # nebeneinander, und bei 1080 bekam die linke so wenig, dass der
        # Kunde auf *Soundc…* zusammenschob. Wer das Fenster schon
        # gespeichert hat, behält seine Größe — das hier gilt nur fuer
        # neue Installationen.
        self.fenster.resize(1240, 700)

        self.einstellungen = QSettings("New Air Media Group", "Faktur")

        #: Die offenen Dokumentfenster. Sie leben weiter, wenn man
        #: sie schliesst; ohne Liste wuerden sie beim naechsten Fenster
        #: eingesammelt und zerstoert.
        self._angebote: list[object] = []

        self.leiste = QListWidget()
        self.leiste.setObjectName("leiste")
        self.leiste.setFixedWidth(212)
        self.leiste.setFrameShape(QListWidget.Shape.NoFrame)
        self.leiste.setSpacing(1)
        self.reihenfolge = [schluessel for schluessel, _t, _k in BEREICHE]

        #: Die Befehle. Sie liegen an zwei Stellen im Fenster — im Menü
        #: und auf dem Balken — und es sind immer dieselben Objekte.
        self.befehle = Befehle(self.fenster)
        for schluessel, titel, _kuerzel in BEREICHE:
            eintrag = QListWidgetItem(titel)
            eintrag.setData(Qt.ItemDataRole.UserRole, schluessel)
            self.leiste.addItem(eintrag)
        self.leiste.currentRowChanged.connect(self._gewechselt)

        # Der Rand aussen herum. ``setContentsMargins`` auf der Liste selbst
        # greift nicht, weil sie ihre Schrift direkt an den Rand des
        # Bildausschnitts setzt.
        self.rahmen = QWidget()
        self.rahmen.setObjectName("rahmen")
        rahmen_anordnung = QVBoxLayout(self.rahmen)
        rahmen_anordnung.setContentsMargins(12, 10, 8, 10)
        rahmen_anordnung.setSpacing(0)
        rahmen_anordnung.addWidget(self.leiste)

        self.seiten: dict[str, Seite] = {
            "uebersicht": UebersichtSeite(verbindung),
            "projekte": self._projektseite(verbindung),
            "dokumente": self._dokumentseite(verbindung),
            "offen": OffeneSeite(verbindung),
            "kunden": KundenSeite(verbindung),
            "leistungen": LeistungenSeite(verbindung),
            "stammdaten": StammdatenSeite(verbindung),
        }

        self.buehne = QStackedWidget()
        for schluessel in self.reihenfolge:
            seite = self.seiten[schluessel]
            # Jede Seite kennt das Fenster, in dem sie steckt. Sonst
            # findet sie es nicht — es ist keine QObject, also kein
            # Elternteil, das man ablaufen koennte.
            seite.fenster = self  # type: ignore[attr-defined]
            self.buehne.addWidget(seite)

        self.trenner = QSplitter(Qt.Orientation.Horizontal)
        self.trenner.setObjectName("trenner")
        self.trenner.addWidget(self.rahmen)
        self.trenner.addWidget(self.buehne)
        self.trenner.setStretchFactor(1, 1)
        self.trenner.setChildrenCollapsible(False)
        self.trenner.setHandleWidth(1)

        huelle = QWidget()
        aussen = QVBoxLayout(huelle)
        aussen.setContentsMargins(0, 0, 0, 0)
        aussen.setSpacing(0)
        aussen.addWidget(self.trenner)
        self.fenster.setCentralWidget(huelle)

        self.fenster.statusBar().showMessage("Bereit")

        self._befehle_verbinden()
        self._menue_bauen()
        self._werkzeug_bauen()
        self._lage_laden()
        self.leiste.setCurrentRow(0)

    # -------------------------------------------------------------- anzeigen

    def zeige(self) -> None:
        """Zeigt das Fenster.

        Returns:
            Nichts.
        """
        self.fenster.show()

    # --------------------------------------------------------------- bereiche

    def _dokumentseite(self, verbindung: sqlite3.Connection) -> DokumenteSeite:
        """Baut die Dokumentenliste und haengt sie an das Fenster.

        Der Doppelklick auf einen Beleg soll ihn oeffnen. Die Liste weiss
        nichts vom Fenster und das Fenster nichts von der Liste — deshalb
        wird der Weg hier einmal gebuehrt, statt in einer von beiden
        festverdrahtet zu sein.

        Args:
            verbindung: Die Datenbankverbindung.

        Returns:
            Die Dokumentenliste.
        """
        seite = DokumenteSeite(verbindung)
        seite.geoeffnet = self._dokument_geoeffnet
        return seite

    def _projektseite(self, verbindung: sqlite3.Connection) -> ProjekteSeite:
        """Baut die Projektseite und haengt sie an das Fenster.

        Wie bei der Dokumentenliste: Die Seite weiss nichts vom Fenster,
        das Fenster nichts von der Seite. Der Weg vom Doppelklick zum
        Fenster wird hier einmal gebuehrt.

        Args:
            verbindung: Die Datenbankverbindung.

        Returns:
            Die Projektseite.
        """
        seite = ProjekteSeite(verbindung)
        seite.geoeffnet = self._dokument_geoeffnet
        return seite

    def gehe(self, schluessel: str) -> None:
        """Springt in einen Bereich der Seitenleiste.

        Args:
            schluessel: Der Schlüssel aus :data:`BEREICHE`.

        Returns:
            Nichts.
        """
        if schluessel in self.reihenfolge:
            self.leiste.setCurrentRow(self.reihenfolge.index(schluessel))

    def neu_laden(self) -> None:
        """Lädt alle Seiten neu, etwa nach einer Änderung in den Stammdaten.

        Returns:
            Nichts.
        """
        for seite in self.seiten.values():
            seite.erneut_laden()

    def melde(self, text: str) -> None:
        """Schreibt einen Satz in die Statuszeile.

        Args:
            text: Was geschehen ist.

        Returns:
            Nichts.
        """
        self.fenster.statusBar().showMessage(text)

    def seite(self) -> Seite:
        """Gibt die Seite, die gerade offen ist.

        Returns:
            Die Seite.
        """
        return self.seiten[self.reihenfolge[self.buehne.currentIndex()]]

    # ------------------------------------------------------------------ lage

    def _lage_laden(self) -> None:
        """Sucht die zuletzt benutzte Größe und Lage.

        Returns:
            Nichts.
        """
        lage = self.einstellungen.value("fenster/lage")
        if isinstance(lage, (bytes, bytearray)):
            self.fenster.restoreGeometry(bytes(lage))

    def lage_speichern(self) -> None:
        """Merkt sich Größe und Lage für den nächsten Start.

        Returns:
            Nichts.
        """
        self.einstellungen.setValue("fenster/lage", self.fenster.saveGeometry())

    # ------------------------------------------------------------------ menue

    def _befehle_verbinden(self) -> None:
        """Hängt jeden Befehl an das, was er tun soll.

        Returns:
            Nichts.
        """
        b = self.befehle
        b.verbinde(b.kunde, self._neu)
        b.verbinde(b.oeffnen, self._dokument_geoeffnet)
        b.verbinde(b.angebot, self._neues_angebot)
        b.verbinde(b.abrechnen, self._abrechnen)
        b.verbinde(b.aendern, self._aendern)
        b.verbinde(b.loeschen, self._loeschen)
        b.verbinde(b.stilllegen, self._stilllegen)
        b.verbinde(b.suchen, self._suchen)
        b.verbinde(b.exportieren, self._exportieren)

    def _menue_bauen(self) -> None:
        """Baut die Menüleiste aus den Befehlen.

        Returns:
            Nichts.
        """
        leiste = self.fenster.menuBar()
        self._menue_datei(leiste)
        self._menue_ansicht(leiste)
        self._menue_faktur(leiste)

    def _menue_datei(self, leiste: QMenuBar) -> None:
        """Baut das Menü *Datei*.

        Args:
            leiste: Die Menüleiste.

        Returns:
            Nichts.
        """
        datei = leiste.addMenu("&Datei")
        b = self.befehle

        for aktion in (b.kunde, b.oeffnen, b.angebot, b.abrechnen):
            datei.addAction(aktion)
        datei.addSeparator()
        for aktion in (b.aendern, b.loeschen, b.stilllegen):
            datei.addAction(aktion)
        datei.addSeparator()
        for aktion in (b.suchen, b.exportieren):
            datei.addAction(aktion)

    def _menue_ansicht(self, leiste: QMenuBar) -> None:
        """Baut das Menü *Ansicht*.

        Die Häkchen hier und die Auswahl links bleiben synchron — sie
        zeigen beide denselben Bereich.

        Args:
            leiste: Die Menüleiste.

        Returns:
            Nichts.
        """
        ansicht = leiste.addMenu("&Ansicht")

        gruppe = QActionGroup(self.fenster)
        gruppe.setExclusive(True)
        self._sprung: dict[str, QAction] = {}

        for schluessel, titel, kuerzel in BEREICHE:
            sprung = QAction(titel, self.fenster)
            sprung.setCheckable(True)
            sprung.setShortcut(kuerzel)
            sprung.triggered.connect(
                lambda _geprueft=False, ziel=schluessel: self.gehe(ziel)
            )
            gruppe.addAction(sprung)
            ansicht.addAction(sprung)
            self._sprung[schluessel] = sprung

    def _menue_faktur(self, leiste: QMenuBar) -> None:
        """Baut das Menü *Faktur*.

        Args:
            leiste: Die Menüleiste.

        Returns:
            Nichts.
        """
        faktur = leiste.addMenu("&Faktur")

        einstellungen = QAction("Einstellungen…", self.fenster)
        einstellungen.setShortcut("Ctrl+,")
        einstellungen.setMenuRole(QAction.MenuRole.PreferencesRole)
        einstellungen.triggered.connect(lambda: self.gehe("stammdaten"))
        faktur.addAction(einstellungen)

        ueber = QAction(f"Über Faktur {__version__}", self.fenster)
        ueber.setMenuRole(QAction.MenuRole.AboutRole)
        ueber.triggered.connect(self._ueber_gezeigt)
        faktur.addAction(ueber)

        beenden = QAction("Faktur beenden", self.fenster)
        beenden.setShortcut("Ctrl+Q")
        beenden.setMenuRole(QAction.MenuRole.QuitRole)
        beenden.triggered.connect(self.fenster.close)
        faktur.addAction(beenden)

    def _werkzeug_bauen(self) -> None:
        """Baut den Balken über dem Fenster.

        **Auf dem Mac ein Teil der Titelleiste.** Ohne das steht ein
        zweiter Streifen unter dem Titel, und das sieht nach zwei
        Bedienleisten aus. ``setUnifiedTitleAndToolBarOnMac`` holt ihn
        nach oben, wo er hingehört.

        Returns:
            Nichts.
        """
        leiste = QToolBar("Werkzeuge")
        leiste.setObjectName("werkzeug")
        leiste.setMovable(False)
        leiste.setFloatable(False)
        leiste.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        b = self.befehle
        leiste.addAction(b.kunde)
        leiste.addSeparator()
        leiste.addAction(b.angebot)
        leiste.addAction(b.abrechnen)

        # Der Rest bleibt rechts. So wie in Velox: was man oft braucht,
        # links; was man ab und an braucht, rechts.
        luft = QWidget()
        luft.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        leiste.addWidget(luft)

        leiste.addAction(b.exportieren)

        self.fenster.addToolBar(Qt.ToolBarArea.TopToolBarArea, leiste)
        self.fenster.setUnifiedTitleAndToolBarOnMac(True)
        self.werkzeug = leiste

    def _gewechselt(self, zeile: int) -> None:
        """Wechselt in den gewaehlten Bereich.

        Args:
            zeile: Die Nummer der Zeile in der Seitenleiste.

        Returns:
            Nichts.
        """
        if not (0 <= zeile < len(self.reihenfolge)):
            return
        schluessel = self.reihenfolge[zeile]
        self.buehne.setCurrentIndex(zeile)
        self.seiten[schluessel].beim_zeigen()
        self.einstellungen.setValue("fenster/bereich", schluessel)
        aktion = getattr(self, "_sprung", {}).get(schluessel)
        if aktion is not None:
            aktion.setChecked(True)

    def _aktion(self, name: str) -> object:
        """Holt eine der vier Aktionen der aktuellen Seite.

        Nicht jede Seite kann alles: Die Dokumentenliste kann nichts
        anlegen. Für sie gibt es nur *Ändern*, und das kommt mit dem
        Dokumentfenster in einer späteren Stufe.

        Args:
            name: ``neu``, ``aendern``, ``loeschen`` oder ``stilllegen``.

        Returns:
            Die Methode, die man aufrufen kann, oder ``None``.
        """
        aktionen = getattr(self.seite(), "aktionen", None)
        if aktionen is None:
            self.melde("Diese Liste lässt sich hier nicht bearbeiten.")
            return None
        return getattr(aktionen, name, None)

    def _neues_angebot(self) -> None:
        """Öffnet ein leeres Fenster für ein Angebot.

        Returns:
            Nichts.
        """
        from faktur.gui.editor import EditorFenster

        fenster = EditorFenster(self.db, eltern=self.fenster)
        fenster.show()
        self._angebote.append(fenster)

    def _abrechnen(self) -> None:
        """Öffnet ein Angebot zum Abrechnen.

        Geht nur, wenn auf der Dokumentenliste gerade ein Angebot steht.
        Ein Angebot ist die Grundlage einer Rechnung, und raten wäre hier
        falsch.

        Returns:
            Nichts.
        """
        from faktur.gui.editor import EditorFenster

        dokument = self._angebot_gewaehlt()
        if dokument is None:
            self.melde("Erst ein Angebot markieren, dann abrechnen.")
            return

        fenster = EditorFenster(
            self.db, angebots_id=int(dokument["id"]), eltern=self.fenster
        )
        fenster.show()
        self._angebote.append(fenster)

    def _angebot_gewaehlt(self) -> object:
        """Gibt das markierte Angebot zurück.

        Returns:
            Das Angebot, oder ``None``, wenn keines markiert ist.
        """
        self.gehe("dokumente")
        dokument = self.seite().gewaehlt()
        if dokument is None or dokument["art"] != "angebot":
            return None
        return dokument

    def _dokument_geoeffnet(self) -> None:
        """Öffnet das markierte Dokument zum Ändern.

        Returns:
            Nichts.
        """
        from faktur.gui.editor import EditorFenster

        dokument = self.seite().gewaehlt()
        if dokument is None:
            self.melde("Erst ein Dokument markieren.")
            return
        fenster = EditorFenster(
            self.db, dokument_id=int(dokument["id"]), eltern=self.fenster
        )
        fenster.show()
        self._angebote.append(fenster)

    def _neu(self) -> None:
        """Legt einen neuen Eintrag an.

        Returns:
            Nichts.
        """
        was = self._aktion("neu")
        if was is not None:
            was()

    def _aendern(self) -> None:
        """Ändert den markierten Eintrag.

        Returns:
            Nichts.
        """
        was = self._aktion("aendern")
        if was is not None:
            was()

    def _loeschen(self) -> None:
        """Löscht den markierten Eintrag.

        Returns:
            Nichts.
        """
        was = self._aktion("loeschen")
        if was is not None:
            was()

    def _stilllegen(self) -> None:
        """Legt den markierten Eintrag still.

        Returns:
            Nichts.
        """
        was = self._aktion("stilllegen")
        if was is not None:
            was()

    def _exportieren(self) -> None:
        """Sagt, dass der Export noch nicht da ist.

        **Der Knopf muss etwas sagen.** Ein Balkenknopf ohne Wirkung sieht
        aus wie ein Programm, das klemmt — schlimmer als ein Knopf, den es
        nicht gibt.

        Returns:
            Nichts.
        """
        self.melde("Der Export für den Steuerberater kommt als Nächstes.")

    def _suchen(self) -> None:
        """Springt in das Suchfeld der aktuellen Seite.

        Returns:
            Nichts.
        """
        feld = getattr(self.seite(), "suchfeld", None)
        if feld is not None:
            feld.setFocus()
            feld.selectAll()

    def _ueber_gezeigt(self) -> None:
        """Zeigt den Übernachweis.

        Returns:
            Nichts.
        """
        QMessageBox.about(
            self.fenster,
            "Über Faktur",
            f"<b>Faktur {__version__}</b><br>Angebote und Rechnungen für die "
            "New Air Media Group.",
        )


__all__ = ["BEREICHE", "Fenster"]
