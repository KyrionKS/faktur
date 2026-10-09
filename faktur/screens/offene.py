"""Der Bildschirm mit den offenen Forderungen.

Er beantwortet die Frage, die bei Rechnungen die wichtigste ist: Was ist
noch offen? Nicht, weil hier gemahnt würde — Mahnwesen ist bewusst nicht
dabei —, sondern weil eine unbeachtete Rechnung das teuerste Ergebnis
dieses Programms wäre.

Das Programm macht keine Sicherungen. Den Ordner ``daten/`` kopiert man
selbst; das steht so auch in der Anleitung.
"""

from __future__ import annotations

import sqlite3
from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from faktur import betraege, dateien, offen
from faktur.basis import BasisScreen
from faktur.suchen import Suchfeld, SuchZeile, sichtbar
from faktur.widgets import Tabelle


class OffeneScreen(BasisScreen):
    """Die offenen Rechnungen, mit Summe und Markierung.

    Attributes:
        posten: Die Rechnungen, wie sie gerade gezeigt werden.
    """

    BINDINGS = [
        Binding("b", "bezahlt", "Als bezahlt markieren", show=True),
        Binding("space", "bezahlt", "Als bezahlt markieren", show=False),
        Binding("suche", "suchen", "Suchen", show=True),
    ]

    def __init__(self, verbindung: sqlite3.Connection) -> None:
        """Legt den Bildschirm an.

        Args:
            verbindung: Die Datenbankverbindung.
        """
        super().__init__(verbindung)
        #: Alle offenen Rechnungen, ungefiltert. Die gefilterte Liste steht in
        #: ``self.posten``. Beide zu vermischen macht die Liste zur
        #: Einbahnstrasse: Nach dem Filtern ist nichts mehr da, was ein
        #: Backspace zurueckholen koennte.
        self.alle_posten: list = []
        self.posten: list = []
        self._suche = ""

    def inhalt(self) -> ComposeResult:
        """Baut die Liste.

        Yields:
            Die Kindelemente.
        """
        yield Suchfeld(self._suche_geaendert)
        yield SuchZeile(id="hinweis")

        yield Tabelle(
            [
                ("Nummer", 10),
                ("Kunde", 28),
                ("Fällig", 12),
                ("Betrag", 14),
                ("Zustand", 14),
            ],
            [],
        )
        yield Static("", id="summe", classes="hinweis")

    def start_fokus(self) -> None:
        """Setzt den Fokus auf die Liste."""
        self.query_one(Tabelle).focus()

    def on_screen_resume(self) -> None:
        """Liest die Liste neu ein."""
        self.aktualisieren()

    def aktualisieren(self) -> None:
        """Holt die offenen Rechnungen und zeichnet neu."""
        self.alle_posten = offen.offene(self.db)
        self.posten = list(self.alle_posten)
        self._suche = ""
        self._zeichne()

    def _suche_geaendert(self, begriff: str) -> None:
        """Sucht weiter, während getippt wird.

        Args:
            begriff: Der Text im Suchfeld.
        """
        self._suche = begriff
        self._zeichne()

    def action_suchen(self) -> None:
        """Legt den Cursor ins Suchfeld.

        Bis 0.8.2 stand das Feld auf diesem Bildschirm, und es war nur mit
        zweimal ``tab`` zu erreichen — ohne dass irgendwo davon die Rede
        war. Die Suche war damit vorhanden und trotzdem tot.
        """
        self.query_one(Suchfeld).focus()

    def _zeile(self, posten: object) -> list[str]:
        """Baut die Textzeile einer Rechnung.

        Args:
            posten: Die Rechnung.

        Returns:
            Die Zellen der Tabellenzeile.
        """
        ueberfaellig = offen.ist_faellig(posten, date.today().isoformat())
        zustand = "überfällig" if ueberfaellig else "offen"

        return [
            posten["nummer"],
            posten["firma"],
            betraege.datum(posten["faellig"]),
            betraege.euro(dateien.summe_von(self.db, posten["id"])),
            zustand,
        ]

    def _zeichne(self) -> None:
        """Zeichnet die Liste mit dem, was zur Suche passt.

        ``self.posten`` wird auf das Ergebnis gesetzt, weil die Aktionen
        darüber auf die markierte Zeile gehen. Vorher stand hier ein
        ``filtern`` über die Zeilen und danach ein Rücksprung über die
        Kennung — zwei Schritte, von denen einer vergessen werden konnte.
        Genau das ist auf der Kundenliste passiert.
        """
        paare = sichtbar(
            self.alle_posten,
            [self._zeile(p) for p in self.alle_posten],
            self._suche,
        )

        self.posten = [posten for posten, _zeile_ in paare]

        tabelle = self.query_one(Tabelle)
        tabelle.zeilen = [zeile for _posten, zeile in paare]
        tabelle.index = min(tabelle.index, max(0, len(paare) - 1))
        tabelle.refresh()

        summe = sum(dateien.summe_von(self.db, posten["id"]) for posten in self.posten)
        self.query_one(SuchZeile).zeige(
            len(paare),
            len(self.alle_posten),
            self._suche,
            "Rechnungen",
            "Rechnung",
        )
        self.query_one("#summe", Static).update(  # type: ignore[arg-type]
            f"Offen: {betraege.euro(summe)}"
            + ("   ·   b oder Leertaste: als bezahlt markieren" if self.posten else "")
        )

    def action_bezahlt(self) -> None:
        """Vermerkt die markierte Rechnung als bezahlt.

        Args:
            None
        """
        tabelle = self.query_one(Tabelle)
        if tabelle.index >= len(self.posten):
            return

        posten = self.posten[tabelle.index]
        offen.als_bezahlt_markieren(self.db, posten["id"], betraege.heute())

        # ``alle_posten`` neu laden, nicht ``posten``: Aus der gefilterten
        # Liste zu zeichnen hiesse, die gerade Rechnung wieder zu zeigen.
        # Der Suchbegriff bleibt, sonst waere die Suche nach dem Markieren
        # weg, ohne dass man sie angeruehrt haette.
        self.alle_posten = offen.offene(self.db)
        self._zeichne()
        self.meldung(f"Rechnung {posten['nummer']} als bezahlt vermerkt.", gut=True)
