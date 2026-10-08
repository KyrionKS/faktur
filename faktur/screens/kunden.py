"""Die Bildschirme für Kunden: Liste, Formular und Detailansicht."""

from __future__ import annotations

import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from faktur import betraege, dateien
from faktur.basis import BasisScreen
from faktur.suchen import Suchfeld, SuchZeile, filtern
from faktur.widgets import Formular, Tabelle

#: Die Felder des Kundenformulars.
FELDER = [
    ("firma", "Firma", ""),
    ("ansprechpartner", "Ansprechpartner", "Vor- und Nachname"),
    ("strasse", "Strasse", "Musterstrasse 1"),
    ("plz", "PLZ", "12345"),
    ("ort", "Ort", "Berlin"),
    ("email", "E-Mail", "name@firma.de"),
    ("telefon", "Telefon", ""),
    ("notiz", "Notiz", "Zahlungsziel, Besonderheiten"),
]


def _zeile(kunde: sqlite3.Row) -> list[str]:
    """Baut eine Listenzeile aus einem Kunden.

    Args:
        kunde: Der Kunde aus der Datenbank.

    Returns:
        Die Zellen der Zeile.
    """
    stadt = " ".join(teil for teil in (kunde["plz"], kunde["ort"]) if teil)
    return [
        kunde["firma"],
        kunde["ansprechpartner"],
        stadt,
        kunde["email"] or kunde["telefon"],
    ]


class KundenListeScreen(BasisScreen):
    """Die Liste aller Kunden."""

    BINDINGS = [
        Binding("n", "neu", "Neuer Kunde", show=True),
        Binding("suche", "suchen", "Suchen", show=True),
    ]

    def __init__(self, verbindung: sqlite3.Connection) -> None:
        """Legt den Bildschirm an.

        Args:
            verbindung: Die Datenbankverbindung.
        """
        super().__init__(verbindung)
        self._suche = ""
        self.kunden = dateien.kunden(verbindung)

    def inhalt(self) -> ComposeResult:
        """Baut die Liste.

        Yields:
            Die Kindelemente.
        """
        yield Suchfeld(self._suche_geaendert)
        yield SuchZeile(id="hinweis")
        yield Tabelle(
            [("Firma", 28), ("Ansprechpartner", 20), ("Ort", 18), ("Kontakt", 24)],
            [_zeile(kunde) for kunde in self.kunden],
        )

    def start_fokus(self) -> None:
        """Legt den Fokus auf die Kundenliste."""
        self.query_one(Tabelle).focus()

    def on_screen_resume(self) -> None:
        """Liest die Liste neu ein, wenn man von einem Formular zurückkommt."""
        self.aktualisieren()

    def aktualisieren(self) -> None:
        """Holt die Kunden aus der Datenbank und zeichnet die Liste neu."""
        self.kunden = dateien.kunden(self.db)
        self._suche = ""

        self._suche_anwenden()

    def _suche_geaendert(self, begriff: str) -> None:
        """Sucht weiter, während getippt wird.

        Args:
            begriff: Der Text im Suchfeld.
        """
        self._suche = begriff
        self._suche_anwenden()

    def _suche_anwenden(self) -> None:
        """Zeichnet die Liste mit dem, was zur Suche passt."""
        alle = [_zeile(kunde) for kunde in self.kunden]
        passend = filtern(alle, self._suche)

        tabelle = self.query_one(Tabelle)
        tabelle.zeilen = passend
        tabelle.index = min(tabelle.index, max(0, len(passend) - 1))
        tabelle.refresh()

        self.query_one(SuchZeile).zeige(
            len(passend), len(alle), self._suche, "Kunden", "Kunde"
        )

    def action_suchen(self) -> None:
        """Legt den Cursor ins Suchfeld.

        Seit es die Kundenliste gibt, stand diese Taste in der Fußzeile und
        tat nichts. Sie ist endlich verdrahtet.
        """
        self.query_one(Suchfeld).focus()

    def action_neu(self) -> None:
        """Öffnet das Formular für einen neuen Kunden."""
        self.app.push_screen(KundeFormularScreen(self.db))

    def on_tabelle_gewaehlt(self, event: Tabelle.Gewaehlt) -> None:
        """Öffnet den gewählten Kunden.

        Args:
            event: Die Nachricht der Tabelle.
        """
        if event.zeile < len(self.kunden):
            self.app.push_screen(
                KundeDetailScreen(self.db, self.kunden[event.zeile]["id"])
            )

    def on_tabelle_bearbeiten(self, event: Tabelle.Bearbeiten) -> None:
        """Öffnet das Formular zum Ändern.

        Args:
            event: Die Nachricht der Tabelle.
        """
        if event.zeile < len(self.kunden):
            self.app.push_screen(
                KundeFormularScreen(self.db, kunde_id=self.kunden[event.zeile]["id"])
            )

    def on_tabelle_loeschen(self, event: Tabelle.Loeschen) -> None:
        """Fragt nach und löscht dann.

        Args:
            event: Die Nachricht der Tabelle.
        """
        if event.zeile < len(self.kunden):
            self._zu_loeschen = self.kunden[event.zeile]["id"]
            self.bestaetigen(
                f"{self.kunden[event.zeile]['firma']} wirklich löschen? "
                "Die Dokumente des Kunden gehen mit."
            )

    _zu_loeschen: int | None = None

    def bestaetigt(self) -> None:
        """Löscht den Kunden, nachdem ja gewählt wurde."""
        if self._zu_loeschen is not None:
            dateien.kunde_loeschen(self.db, self._zu_loeschen)
            self._zu_loeschen = None
            self.aktualisieren()
            self.hinweis("Kunde gelöscht.")


class KundeFormularScreen(BasisScreen):
    """Ein Kunde anlegen oder ändern."""

    def __init__(
        self, verbindung: sqlite3.Connection, kunde_id: int | None = None
    ) -> None:
        """Legt den Bildschirm an.

        Args:
            verbindung: Die Datenbankverbindung.
            kunde_id: Der Kunde, der geändert werden soll, sonst ``None``.
        """
        super().__init__(verbindung)
        self.kunde_id = kunde_id

    def inhalt(self) -> ComposeResult:
        """Baut das Formular.

        Yields:
            Die Kindelemente.
        """
        werte: dict[str, str] = {}
        if self.kunde_id is not None:
            kunde = dateien.kunde_holen(self.db, self.kunde_id)
            if kunde:
                werte = {feld: kunde[feld] or "" for feld, _, _ in FELDER}

        yield Formular(FELDER, werte)

    def start_fokus(self) -> None:
        """Legt den Cursor ins erste Feld."""
        self.query_one(Formular).focus_first()

    def on_formular_fertig(self, event: Formular.Fertig) -> None:
        """Speichert den Kunden.

        Args:
            event: Die Nachricht des Formulars.
        """
        if not event.werte.get("firma"):
            self.meldung("Ohne Firma geht es nicht.", gut=False)
            return

        dateien.kunde_speichern(self.db, event.werte, self.kunde_id)
        self.app.pop_screen()
        self.hinweis("Kunde gespeichert." if self.kunde_id is None else "Geändert.")

    def on_formular_verloren(self) -> None:
        """Geht zurück, ohne zu speichern."""
        self.app.pop_screen()


class KundeDetailScreen(BasisScreen):
    """Ein Kunde mit allen seinen Dokumenten."""

    BINDINGS = [
        Binding("f2", "bearbeiten", "Ändern", show=True),
    ]

    def __init__(self, verbindung: sqlite3.Connection, kunde_id: int) -> None:
        """Legt den Bildschirm an.

        Args:
            verbindung: Die Datenbankverbindung.
            kunde_id: Der Kunde, der gezeigt werden soll.
        """
        super().__init__(verbindung)
        self.kunde_id = kunde_id

    def inhalt(self) -> ComposeResult:
        """Baut die Detailansicht.

        Yields:
            Die Kindelemente.
        """
        kunde = dateien.kunde_holen(self.db, self.kunde_id)
        if kunde is None:
            yield Static("Dieser Kunde gibt es nicht mehr.")
            return

        yield Static(f"{kunde['firma']}", classes="detail_titel")

        anschrift = " · ".join(
            teil
            for teil in (
                kunde["strasse"],
                " ".join(t for t in (kunde["plz"], kunde["ort"]) if t),
            )
            if teil
        )
        for zeile in (
            anschrift,
            " ".join(t for t in (kunde["telefon"], kunde["email"]) if t),
            kunde["notiz"],
        ):
            if zeile:
                yield Static(zeile, classes="detail_zeile")

        dokumente = [
            d for d in dateien.dokumente(self.db) if d["kunde_id"] == self.kunde_id
        ]

        if dokumente:
            yield Static("", classes="abstand")
            yield Static("Dokumente", classes="detail_kopf")
            for dokument in dokumente:
                summe = dateien.summe_von(self.db, dokument["id"])
                art = "Angebot" if dokument["art"] == "angebot" else "Rechnung"
                yield Static(
                    f"  {dokument['datum']}  {art:<9} {dokument['nummer']:<16}"
                    f" {betraege.euro(summe)}",
                    classes="detail_zeile",
                )
        else:
            yield Static("Noch keine Dokumente.", classes="detail_zeile")

    def action_bearbeiten(self) -> None:
        """Öffnet das Formular zum Ändern."""
        self.app.push_screen(KundeFormularScreen(self.db, kunde_id=self.kunde_id))
