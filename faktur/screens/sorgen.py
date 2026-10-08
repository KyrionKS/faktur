"""Die beiden Bildschirme, die um Sorgen kümmern.

**Offene Forderungen** beantwortet die Frage, die bei Rechnungen die
wichtigste ist: Was ist noch offen? Nicht, weil hier gemahnt würde —
Mahnwesen ist bewusst nicht dabei —, sondern weil eine unbeachtete
Rechnung das teuerste Ergebnis dieses Programms wäre.

**Sichern** kopiert den Datenordner. Auf einer Platte, ohne Kopie, ist der
ganze Bestand irgendwann weg, und bei einem Angebot, das schon beim Kunden
liegt, gibt es kein Zurück: Die Nummer steht gedruckt auf einem Dokument,
das niemandem mehr gehört.
"""

from __future__ import annotations

import sqlite3
from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from faktur import betraege, dateien, offen, sichern
from faktur.basis import BasisScreen
from faktur.suchen import Suchfeld, SuchZeile, filtern
from faktur.widgets import Tabelle


class OffeneScreen(BasisScreen):
    """Die offenen Rechnungen, mit Summe und Markierung.

    Attributes:
        posten: Die Rechnungen, wie sie gerade gezeigt werden.
    """

    BINDINGS = [
        Binding("b", "bezahlt", "Als bezahlt markieren", show=True),
        Binding("space", "bezahlt", "Als bezahlt markieren", show=False),
    ]

    def __init__(self, verbindung: sqlite3.Connection) -> None:
        """Legt den Bildschirm an.

        Args:
            verbindung: Die Datenbankverbindung.
        """
        super().__init__(verbindung)
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
        self.posten = offen.offene(self.db)
        self._suche = ""
        self._zeichne()

    def _suche_geaendert(self, begriff: str) -> None:
        """Sucht weiter, während getippt wird.

        Args:
            begriff: Der Text im Suchfeld.
        """
        self._suche = begriff
        self._zeichne()

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
        """Zeichnet die Liste mit dem, was zur Suche passt."""
        zeilen = [self._zeile(p) for p in self.posten]
        passend = filtern(zeilen, self._suche)
        nummern = {zeile[0] for zeile in passend}

        self.posten = [
            p for p, z in zip(self.posten, zeilen, strict=True) if z[0] in nummern
        ]

        tabelle = self.query_one(Tabelle)
        tabelle.zeilen = [z for z in zeilen if z[0] in nummern]
        tabelle.index = min(tabelle.index, max(0, len(tabelle.zeilen) - 1))
        tabelle.refresh()

        summe = sum(dateien.summe_von(self.db, posten["id"]) for posten in self.posten)
        self.query_one(SuchZeile).zeige(
            len(nummern),
            len(zeilen),
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

        self.posten = offen.offene(self.db)
        self._zeichne()
        self.meldung(f"Rechnung {posten['nummer']} als bezahlt vermerkt.", gut=True)


class SichernScreen(BasisScreen):
    """Kopiert den Datenordner und zeigt, was schon gesichert ist."""

    BINDINGS = [Binding("n", "neu", "Jetzt sichern", show=True)]

    def __init__(self, verbindung: sqlite3.Connection) -> None:
        """Legt den Bildschirm an.

        Args:
            verbindung: Die Datenbankverbindung.
        """
        super().__init__(verbindung)

    def inhalt(self) -> ComposeResult:
        """Baut die Anzeige.

        Yields:
            Die Kindelemente.
        """
        yield Static(
            "Der Ordner daten/ ist der ganze Bestand: Kunden, Leistungen, "
            "jedes Angebot, jede Rechnung und die PDF dazu.\n"
            "n sichert jetzt. Die alten Sicherungen bleiben liegen.",
            classes="hinweis",
            id="erklaerung",
        )
        yield Static("", id="liste")

    def start_fokus(self) -> None:
        """Nichts zu bedienen, ausser den Tasten."""
        return

    def on_screen_resume(self) -> None:
        """Zeigt die vorhandenen Sicherungen."""
        self._zeichne()

    def _zeichne(self) -> None:
        """Schreibt die Liste der Sicherungen."""
        self.query_one("#liste", Static).update("\n".join(sichern.texte()))  # type: ignore[arg-type]

    def action_neu(self) -> None:
        """Sichert jetzt.

        Args:
            None
        """
        try:
            ordner = sichern.sichere()
        except sichern.Fehler as grund:
            self.meldung(str(grund), gut=False)
            return

        self._zeichne()
        self.meldung(f"Gesichert nach {ordner.name}", gut=True)
