"""Die Bildschirme für Stammdaten und Brieftexte.

Firma, Anschrift, Bank und Logo stehen auf jedem Dokument. Diese Felder sind
deshalb das Erste, was ausgefüllt sein sollte.
"""

from __future__ import annotations

import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from faktur import einstellungen, texte
from faktur.basis import BasisScreen
from faktur.db import STANDARD_LOGO
from faktur.editor import Brieftext
from faktur.widgets import Auswahl, Formular

#: Die Felder in der Reihenfolge des Formulars.
FELDER = [
    ("firma", "Firmenname", "New Air Media Group"),
    ("zusatz", "Zusatz", "Tonstudio & Medienproduktion"),
    ("strasse", "Strasse", ""),
    ("plz", "PLZ", ""),
    ("ort", "Ort", ""),
    ("telefon", "Telefon", ""),
    ("email", "E-Mail", ""),
    ("webseite", "Webseite", ""),
    ("inhaber", "Inhaber", ""),
    ("bank", "Bank", ""),
    ("iban", "IBAN", ""),
    ("bic", "BIC", ""),
    ("steuernummer", "Steuernummer", ""),
]


class StammdatenScreen(BasisScreen):
    """Die Punkte der Stammdaten."""

    PUNKTE = (
        ("firma", "1", "Firma und Bank", "Anschrift, Kontakt, IBAN"),
        ("angebot", "2", "Text für Angebote", "Der Brief, der mitgeht"),
        ("rechnung", "3", "Text für Rechnungen", "Der Brief, der mitgeht"),
        ("platzhalter", "4", "Platzhalter", "Was das Programm einsetzen kann"),
        ("aussehen", "5", "Aussehen der PDF", "Größen und was draufsteht"),
    )

    def inhalt(self) -> ComposeResult:
        """Baut die Liste der Punkte.

        Yields:
            Die Kindelemente.
        """
        fehlend = einstellungen.fehlend(self.db)
        if fehlend:
            yield Static(
                "Noch offen: " + ", ".join(fehlend) + ". Punkt 1 füllt das auf.",
                classes="hinweis",
            )

        logopfad = einstellungen.logo_pfad(self.db)
        yield Static(
            "Logo: "
            + (
                str(logopfad)
                if logopfad
                else f"noch keines — leg die Datei als {STANDARD_LOGO} ab"
            ),
            classes="hinweis",
        )

        yield Auswahl(self.PUNKTE, self.auswahl)

    def auswahl(self, aktion: str) -> None:
        """Öffnet den passenden Bildschirm.

        Args:
            aktion: Der Schlüssel des gewählten Punktes.
        """
        if aktion == "firma":
            self.app.push_screen(StammdatenFormularScreen(self.db))
        elif aktion in ("angebot", "rechnung"):
            self.app.push_screen(BausteinScreen(self.db, aktion))
        elif aktion == "platzhalter":
            self.app.push_screen(PlatzhalterScreen(self.db))
        elif aktion == "aussehen":
            from faktur.screens.aussehen import AussehenScreen

            self.app.push_screen(AussehenScreen(self.db))


class StammdatenFormularScreen(BasisScreen):
    """Firma, Anschrift und Bank in einem Formular."""

    def inhalt(self) -> ComposeResult:
        """Baut das Formular.

        Yields:
            Die Kindelemente.
        """
        werte = einstellungen.alle(self.db)
        yield Formular(FELDER, werte)

    def start_fokus(self) -> None:
        """Legt den Cursor ins erste Feld."""
        self.query_one(Formular).focus_first()

    def on_formular_fertig(self, event: Formular.Fertig) -> None:
        """Schreibt alles in die Datenbank.

        Args:
            event: Die Nachricht des Formulars.
        """
        for name, _beschriftung, _vorschlag in FELDER:
            einstellungen.speichere(self.db, name, event.werte.get(name, ""))

        self.app.pop_screen()
        self.hinweis("Stammdaten gespeichert.")

    def on_formular_verloren(self) -> None:
        """Geht zurück, ohne zu speichern."""
        self.app.pop_screen()


class BausteinScreen(BasisScreen):
    """Der Brieftext für Angebote oder Rechnungen.

    Mehrzeilig, weil Absätze durch Leerzeilen getrennt sind. Gespeichert wird
    mit ``Strg+S``, abgebrochen mit ``esc``, der Vorschlag kommt mit ``Strg+R``
    zurück, falls beim Herumtippen alles kaputtgeht.
    """

    BINDINGS = [
        Binding("ctrl+r", "vorschlag", "Vorschlag", show=True),
    ]

    def __init__(self, verbindung: sqlite3.Connection, art: str) -> None:
        """Legt den Bildschirm an.

        Args:
            verbindung: Die Datenbankverbindung.
            art: ``angebot`` oder ``rechnung``.
        """
        super().__init__(verbindung)
        self.art = art

    def inhalt(self) -> ComposeResult:
        """Baut den Editor.

        Yields:
            Die Kindelemente.
        """
        was = "Angebote" if self.art == "angebot" else "Rechnungen"
        yield Brieftext(
            einstellungen.baustein(self.db, self.art),
            f"Text für {was}. Leerzeilen trennen Absätze.",
            vorschlag=lambda: einstellungen.BAUSTEINE_VORSCHLAG.get(
                f"text_{self.art}", ""
            ),
        )

    def start_fokus(self) -> None:
        """Legt den Cursor in den Text."""
        self.query_one(Brieftext).start_fokus()

    def action_vorschlag(self) -> None:
        """Setzt den mitgelieferten Vorschlag zurück."""
        editor = self.query_one(Brieftext)
        editor.vorschlag_einsetzen()
        editor.hinweis("Der Vorschlag steht wieder drin. Strg+S zum Speichern.")
        editor.start_fokus()

    def on_brieftext_gespeichert(self, event: Brieftext.Gespeichert) -> None:
        """Speichert den Baustein und sagt, welche Namen unbekannt sind.

        Args:
            event: Die Nachricht des Editors.
        """
        if not event.text.strip():
            self.meldung(
                "Leerer Text. Nimm den Vorschlag oder schreib etwas.", gut=False
            )
            self.query_one(Brieftext).start_fokus()
            return

        einstellungen.speichere(self.db, f"text_{self.art}", event.text)
        self.app.pop_screen()

        unbekannt = texte.unbekannte(event.text)
        if unbekannt:
            self.hinweis("Gespeichert. Unbekannt: " + ", ".join(unbekannt), gut=False)
        else:
            self.hinweis("Gespeichert.")

    def on_brieftext_verloren(self) -> None:
        """Geht zurück, ohne zu speichern."""
        self.app.pop_screen()


class PlatzhalterScreen(BasisScreen):
    """Eine Übersicht aller Platzhalter, mit Beispiel."""

    def inhalt(self) -> ComposeResult:
        """Baut die Tabelle der Platzhalter.

        Yields:
            Die Kindelemente.
        """
        yield Static(
            "Diese Namen kannst du in den Brieftexten verwenden.", classes="hinweis"
        )
        for name, beispiel in einstellungen.PLATZHALTER.items():
            platzhalter = "{{" + name.ljust(20) + "}}"
            yield Static(f"  {platzhalter} {beispiel}", classes="detail_zeile")
