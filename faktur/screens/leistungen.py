"""Die Bildschirme für die Preisliste."""

from __future__ import annotations

import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from faktur import betraege, dateien
from faktur.basis import BasisScreen
from faktur.widgets import Formular, Tabelle

#: Die Felder des Leistungsformulars.
FELDER = [
    ("bezeichnung", "Bezeichnung", "Aufnahme Ton"),
    ("beschreibung", "Beschreibung", "Was genau dazugehört"),
    ("einheit", "Einheit", "Tag"),
    ("preis", "Preis", "850,00"),
]


class LeistungenScreen(BasisScreen):
    """Die Preisliste mit allem, was das Studio anbietet."""

    BINDINGS = [
        Binding("n", "neu", "Neue Leistung", show=True),
    ]

    def __init__(self, verbindung: sqlite3.Connection) -> None:
        """Legt den Bildschirm an.

        Args:
            verbindung: Die Datenbankverbindung.
        """
        super().__init__(verbindung)
        self.leistungen = dateien.leistungen(verbindung)

    def inhalt(self) -> ComposeResult:
        """Baut die Liste.

        Yields:
            Die Kindelemente.
        """
        yield Static(
            f"{len(self.leistungen)} Leistungen. Enter zeigt, F2 ändert, "
            "Entf nimmt sie aus der Liste.",
            classes="hinweis",
            id="hinweis",
        )
        yield Tabelle(
            [("Bezeichnung", 34), ("Einheit", 12), ("Preis", 14)],
            [
                [
                    leistung["bezeichnung"],
                    leistung["einheit"],
                    betraege.euro(leistung["preis"]),
                ]
                for leistung in self.leistungen
            ],
        )

    def start_fokus(self) -> None:
        """Legt den Fokus auf die Preisliste."""
        self.query_one(Tabelle).focus()

    def on_screen_resume(self) -> None:
        """Liest die Liste neu ein, wenn man von einem Formular zurückkommt."""
        self.aktualisieren()

    def aktualisieren(self) -> None:
        """Holt die Leistungen aus der Datenbank und zeichnet neu."""
        self.leistungen = dateien.leistungen(self.db)
        tabelle = self.query_one(Tabelle)
        tabelle.zeilen = [
            [
                leistung["bezeichnung"],
                leistung["einheit"],
                betraege.euro(leistung["preis"]),
            ]
            for leistung in self.leistungen
        ]
        tabelle.index = min(tabelle.index, max(0, len(tabelle.zeilen) - 1))
        tabelle.refresh()

        self.query_one("#hinweis").update(  # type: ignore[arg-type]
            f"{len(self.leistungen)} Leistungen. Enter zeigt, F2 ändert, "
            "Entf nimmt sie aus der Liste."
        )

    def action_neu(self) -> None:
        """Öffnet das Formular für eine neue Leistung."""
        self.app.push_screen(LeistungFormularScreen(self.db))

    def on_tabelle_bearbeiten(self, event: Tabelle.Bearbeiten) -> None:
        """Öffnet das Formular zum Ändern.

        Args:
            event: Die Nachricht der Tabelle.
        """
        if event.zeile < len(self.leistungen):
            self.app.push_screen(
                LeistungFormularScreen(
                    self.db, leistung_id=self.leistungen[event.zeile]["id"]
                )
            )

    def on_tabelle_loeschen(self, event: Tabelle.Loeschen) -> None:
        """Fragt nach und nimmt sie dann aus der Liste.

        Args:
            event: Die Nachricht der Tabelle.
        """
        if event.zeile < len(self.leistungen):
            self._zu_loeschen = self.leistungen[event.zeile]["id"]
            self.bestaetigen(
                f"„{self.leistungen[event.zeile]['bezeichnung']}“ wirklich "
                "aus der Preisliste nehmen? Alte Dokumente behalten ihren Text."
            )

    _zu_loeschen: int | None = None

    def bestaetigt(self) -> None:
        """Nimmt die Leistung heraus, nachdem ja gewählt wurde."""
        if self._zu_loeschen is not None:
            dateien.leistung_loeschen(self.db, self._zu_loeschen)
            self._zu_loeschen = None
            self.aktualisieren()
            self.hinweis("Leistung aus der Preisliste genommen.")


class LeistungFormularScreen(BasisScreen):
    """Eine Leistung anlegen oder ändern."""

    def __init__(
        self, verbindung: sqlite3.Connection, leistung_id: int | None = None
    ) -> None:
        """Legt den Bildschirm an.

        Args:
            verbindung: Die Datenbankverbindung.
            leistung_id: Die Leistung zum Ändern, sonst ``None``.
        """
        super().__init__(verbindung)
        self.leistung_id = leistung_id

    def inhalt(self) -> ComposeResult:
        """Baut das Formular.

        Yields:
            Die Kindelemente.
        """
        werte: dict[str, str] = {}
        if self.leistung_id is not None:
            leistung = dateien.leistung_holen(self.db, self.leistung_id)
            if leistung:
                werte = {
                    "bezeichnung": leistung["bezeichnung"] or "",
                    "beschreibung": leistung["beschreibung"] or "",
                    "einheit": leistung["einheit"] or "",
                    "preis": betraege.euro(leistung["preis"]).replace(" €", ""),
                }

        yield Formular(FELDER, werte)

    def start_fokus(self) -> None:
        """Legt den Cursor ins erste Feld."""
        self.query_one(Formular).focus_first()

    def on_formular_fertig(self, event: Formular.Fertig) -> None:
        """Speichert die Leistung.

        Args:
            event: Die Nachricht des Formulars.
        """
        if not event.werte.get("bezeichnung"):
            self.meldung("Ohne Bezeichnung geht es nicht.", gut=False)
            return

        dateien.leistung_speichern(self.db, event.werte, self.leistung_id)
        self.app.pop_screen()
        self.hinweis("Leistung gespeichert.")

    def on_formular_verloren(self) -> None:
        """Geht zurück, ohne zu speichern."""
        self.app.pop_screen()
