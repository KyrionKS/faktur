"""Die Textual-Oberfläche.

Textual hält einen echten Bildschirmpuffer: Die Bildschirme beschreiben nur,
wie sie aussehen, und Textual zeichnet die Unterschiede. Deshalb bleibt das
Bild ruhig, wenn man sich mit den Pfeiltasten bewegt, und nichts läuft
über, wenn ein Untermenü zurückkommt.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from faktur import db, einstellungen
from faktur.basis import BasisScreen
from faktur.screens.dokumente import DokumentenScreen, EditorScreen
from faktur.screens.kunden import KundenListeScreen
from faktur.screens.leistungen import LeistungenScreen
from faktur.screens.stammdaten import StammdatenScreen
from faktur.widgets import Auswahl


class MenueScreen(BasisScreen):
    """Die Startseite mit den Punkten."""

    BINDINGS = [
        Binding("escape", "nichts", "", show=False),
    ]

    #: Die Punkte des Menüs: Schlüssel, Nummer, Titel, Erklärung.
    PUNKTE = (
        ("angebot", "1", "Angebot erstellen", "Aus Leistungen ein Angebot bauen"),
        ("rechnung", "2", "Rechnung erstellen", "Aus Leistungen abrechnen"),
        ("kunden", "3", "Kunden", "Kunden anlegen, ansehen, suchen"),
        ("leistungen", "4", "Leistungen", "Die Preisliste pflegen"),
        ("dokumente", "5", "Dokumente", "Angebote und Rechnungen durchsehen"),
        ("stammdaten", "6", "Stammdaten", "Firma, Bank, Logo, Brieftexte"),
        ("pdf", "7", "PDF neu schreiben", "Ein Dokument noch einmal ausgeben"),
        ("ordner", "8", "Rechnungsordner öffnen", "Den Ordner mit den PDF zeigen"),
        ("quit", "q", "Beenden", "Das Programm verlassen"),
    )

    def inhalt(self) -> ComposeResult:
        """Baut die Seite mit den Punkten.

        Yields:
            Die Kindelemente.
        """
        if not einstellungen.vollstaendig(self.db):
            yield Static("Stammdaten fehlen — Punkt 6", id="hinweis")
        yield Auswahl(self.PUNKTE, self.auswahl)

    def action_nichts(self) -> None:
        """Kann nicht zurück, das ist das Hauptmenü."""

    def auswahl(self, aktion: str) -> None:
        """Öffnet den passenden Bildschirm.

        Args:
            aktion: Der Schlüssel des gewählten Punktes.
        """
        if aktion == "quit":
            self.app.exit()
        elif aktion == "angebot":
            self.app.push_screen(EditorScreen(self.db, "angebot"))
        elif aktion == "rechnung":
            self.app.push_screen(EditorScreen(self.db, "rechnung"))
        elif aktion == "kunden":
            self.app.push_screen(KundenListeScreen(self.db))
        elif aktion == "leistungen":
            self.app.push_screen(LeistungenScreen(self.db))
        elif aktion == "dokumente":
            self.app.push_screen(DokumentenScreen(self.db))
        elif aktion == "stammdaten":
            self.app.push_screen(StammdatenScreen(self.db))
        elif aktion == "pdf":
            self.app.push_screen(DokumentenScreen(self.db, nur_drucken=True))
        elif aktion == "ordner":
            self.ordner_oeffnen()

    def ordner_oeffnen(self) -> None:
        """Öffnet den Ordner mit den PDF im Dateimanager des Systems."""
        ordner = db.ausgabeordner()
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", str(ordner)], check=False)
            elif sys.platform.startswith("win"):
                import os

                os.startfile(str(ordner))  # type: ignore[attr-defined]
            else:
                subprocess.run(["xdg-open", str(ordner)], check=False)
        except OSError:
            self.meldung(f"Der Ordner liegt hier: {ordner}", gut=False)


class FakturApp(App[None]):
    """Die Anwendung."""

    CSS_PATH = "app.tcss"
    TITLE = "Faktur"
    SUB_TITLE = "New Air Media Group"

    def __init__(self, datenbankpfad: Path | None = None) -> None:
        """Legt die App an und holt alte Dateien an ihren neuen Ort.

        Args:
            datenbankpfad: Eine andere Datenbank als sonst, für Tests.
        """
        super().__init__()
        self.umgezogen = db.umziehen()
        self.db = db.verbinden(datenbankpfad)

    def on_mount(self) -> None:
        """Startet mit der Startseite."""
        self.push_screen(MenueScreen(self.db))


def main() -> None:
    """Startet das Programm."""
    app = FakturApp()
    for meldung in app.umgezogen:
        print(f"  {meldung}")
    app.run()
