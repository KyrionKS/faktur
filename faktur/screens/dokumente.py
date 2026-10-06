"""Die Bildschirme für Angebote und Rechnungen.

Der Editor baut ein Dokument Schritt für Schritt: Kunde wählen, Positionen
sammeln, nachsehen, speichern. Die PDF entsteht dabei von selbst.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from faktur import betraege, dateien, db, pdf
from faktur.basis import BasisScreen
from faktur.widgets import Auswahl, Formular, Tabelle

#: Die Felder des Dokumentkopfs.
KOPFFELDER_ANGEBOT = [
    ("nummer", "Nummer", ""),
    ("datum", "Datum", ""),
    ("gueltig_bis", "Gültig bis", ""),
    ("notiz", "Notiz", "Nur auf diesem Dokument"),
]

KOPFFELDER_RECHNUNG = [
    ("nummer", "Nummer", ""),
    ("datum", "Datum", ""),
    ("faellig", "Fällig am", ""),
    ("notiz", "Notiz", "Nur auf diesem Dokument"),
]


def dateiname(dokument: sqlite3.Row, art: str) -> str:
    """Baut den Dateinamen einer PDF.

    Angebot und Rechnung liegen im selben Ordner, die Art steht deshalb im
    Namen:

        ANG - 0001 - Soundcheck GmbH
        RE - 0002 - Soundcheck GmbH

    Args:
        dokument: Das Dokument.
        art: ``angebot`` oder ``rechnung``.

    Returns:
        Der Dateiname, ohne Ordner und ohne Endung.
    """
    kennung = "ANG" if art == "angebot" else "RE"
    nummer = _sicher(dokument["nummer"] or str(dokument["id"]))
    kunde = _sicher(dokument["firma"] or "ohne Kunde")
    return f"{kennung} - {nummer} - {kunde}"


def _sicher(text: str) -> str:
    """Entfernt die Zeichen, die im Dateinamen Ärger machen.

    Args:
        text: Der Name.

    Returns:
        Der Name ohne Schrägstriche, Doppelpunkte und Rückschritte.
    """
    for zeichen in '/\\:*?"<>|':
        text = text.replace(zeichen, "-")
    return " ".join(text.split())


class DokumentenScreen(BasisScreen):
    """Die Liste aller Angebote und Rechnungen."""

    BINDINGS = [
        Binding("a", "angebot", "Neues Angebot", show=True),
        Binding("r", "rechnung", "Abrechnen", show=True),
        Binding("enter", "pdf", "PDF neu schreiben", show=True),
    ]

    def __init__(
        self, verbindung: sqlite3.Connection, nur_drucken: bool = False
    ) -> None:
        """Legt den Bildschirm an.

        Args:
            verbindung: Die Datenbankverbindung.
            nur_drucken: Wenn wahr, geht es nur ums nochmalige Schreiben
                der PDF, wie vom Menüpunkt aus.
        """
        super().__init__(verbindung)
        self.nur_drucken = nur_drucken
        self.dokumente = dateien.dokumente(verbindung)

    def inhalt(self) -> ComposeResult:
        """Baut die Liste.

        Yields:
            Die Kindelemente.
        """
        if not self.nur_drucken:
            yield Static(
                f"{len(self.dokumente)} Dokumente. Enter schreibt die PDF "
                "neu, F2 zeigt das Dokument.",
                classes="hinweis",
            )
        else:
            yield Static("Enter schreibt die PDF neu. esc zurück.", classes="hinweis")

        yield Tabelle(
            [
                ("Art", 10),
                ("Nummer", 16),
                ("Kunde", 28),
                ("Datum", 12),
                ("Betrag", 14),
            ],
            [
                [
                    "Angebot" if d["art"] == "angebot" else "Rechnung",
                    d["nummer"],
                    d["firma"],
                    d["datum"],
                    betraege.euro(dateien.summe_von(self.db, d["id"])),
                ]
                for d in self.dokumente
            ],
        )

    def start_fokus(self) -> None:
        """Legt den Fokus auf die Dokumentenliste."""
        self.query_one(Tabelle).focus()

    def on_screen_resume(self) -> None:
        """Liest die Liste neu ein, wenn man von einem Formular zurückkommt."""
        self.aktualisieren()

    def aktualisieren(self) -> None:
        """Holt die Dokumente aus der Datenbank und zeichnet neu."""
        self.dokumente = dateien.dokumente(self.db)
        tabelle = self.query_one(Tabelle)
        tabelle.zeilen = [
            [
                "Angebot" if d["art"] == "angebot" else "Rechnung",
                d["nummer"],
                d["firma"],
                d["datum"],
                betraege.euro(dateien.summe_von(self.db, d["id"])),
            ]
            for d in self.dokumente
        ]
        tabelle.index = min(tabelle.index, max(0, len(tabelle.zeilen) - 1))
        tabelle.refresh()

    def action_angebot(self) -> None:
        """Beginnt ein neues Angebot."""
        self.app.push_screen(EditorScreen(self.db, "angebot"))

    def action_rechnung(self) -> None:
        """Rechnet ab, oder macht aus dem Angebot eine Rechnung.

        Steht die Auswahl auf einem Angebot, wird daraus eine Rechnung. Sonst
        fängt eine neue Rechnung an. So heisst ``r`` immer das Gleiche:
        abrechnen.
        """
        tabelle = self.query(Tabelle)
        if (
            tabelle
            and tabelle.first()
            and tabelle.first().index < len(self.dokumente)
            and self.dokumente[tabelle.first().index]["art"] == "angebot"
        ):
            self.angebot_zu_rechnung()
            return
        self.app.push_screen(EditorScreen(self.db, "rechnung"))

    def action_pdf(self) -> None:
        """Schreibt die PDF des markierten Dokuments neu."""
        self.markiertes_dokument_schreiben()

    def markiertes_dokument_schreiben(self) -> None:
        """Nimmt das markierte Dokument und schreibt die PDF.

        Geht ohne Auswahl nicht, weil es dann nichts zu schreiben gäbe.
        """
        tabelle = self.query_one(Tabelle)
        if tabelle.index >= len(self.dokumente):
            return

        dokument = self.dokumente[tabelle.index]
        voll = dateien.dokument_holen(self.db, dokument["id"])
        if voll is None:
            self.meldung("Das Dokument gibt es nicht mehr.", gut=False)
            return

        ziel = db.ausgabeordner() / f"{dateiname(voll, voll['art'])}.pdf"
        try:
            pdf.erzeugen(self.db, voll, ziel)
        except OSError:
            self.meldung("Die PDF liess sich nicht schreiben.", gut=False)
            return

        self.meldung(f"Geschrieben: {ziel}")

    def angebot_zu_rechnung(self) -> None:
        """Macht aus dem markierten Angebot eine Rechnung.

        Kunde und Positionen wandern mit, samt der Verknüpfung zur
        Preisliste. Offen bleiben nur Nummer, Datum und Fälligkeit, die
        stehen in der Kontrolle.
        """
        tabelle = self.query_one(Tabelle)
        if tabelle.index >= len(self.dokumente):
            return

        dokument = self.dokumente[tabelle.index]
        if dokument["art"] != "angebot":
            self.meldung(
                "Nur aus einem Angebot wird eine Rechnung. Markiert ist eine Rechnung.",
                gut=False,
            )
            return

        try:
            kopf, positionen = dateien.als_angebot_uebernehmen(self.db, dokument["id"])
        except ValueError:
            self.meldung("Das Angebot liess sich nicht lesen.", gut=False)
            return

        editor = EditorScreen(self.db, "rechnung", kopf, positionen, direkt=True)
        self.app.push_screen(editor)

    def on_tabelle_gewaehlt(self, event: Tabelle.Gewaehlt) -> None:
        """Schreibt die PDF des gewählten Dokuments neu.

        Args:
            event: Die Nachricht der Tabelle.
        """
        self.markiertes_dokument_schreiben()

    def on_tabelle_loeschen(self, event: Tabelle.Loeschen) -> None:
        """Fragt nach und löscht dann.

        Args:
            event: Die Nachricht der Tabelle.
        """
        if event.zeile < len(self.dokumente):
            self._zu_loeschen = self.dokumente[event.zeile]["id"]
            self.bestaetigen(
                f"Dokument {self.dokumente[event.zeile]['nummer']} löschen? "
                "Die PDF bleibt im Ordner."
            )

    _zu_loeschen: int | None = None

    def bestaetigt(self) -> None:
        """Löscht das Dokument, nachdem ja gewählt wurde."""
        if self._zu_loeschen is not None:
            dateien.dokument_loeschen(self.db, self._zu_loeschen)
            self._zu_loeschen = None
            self.aktualisieren()
            self.hinweis("Dokument gelöscht.")


class EditorScreen(BasisScreen):
    """Ein Angebot oder eine Rechnung zusammenstellen.

    Drei Schritte nacheinander: Kunde, Positionen, Kontrolle. Jeder Schritt
    ist ein eigener Screen, damit ``esc`` genau eine Ebene zurückgeht.
    """

    def __init__(
        self,
        verbindung: sqlite3.Connection,
        art: str,
        angaben: dict[str, str | int | None] | None = None,
        positionen: list[dict[str, str | float | int | None]] | None = None,
        direkt: bool = False,
    ) -> None:
        """Legt den Editor an.

        Args:
            verbindung: Die Datenbankverbindung.
            art: ``angebot`` oder ``rechnung``.
            angaben: Werte für den Kopf, etwa aus einem Angebot übernommen.
            positionen: Positionen, etwa aus einem Angebot übernommen.
            direkt: Wenn wahr, wird die Kundenauswahl übersprungen. Beim
                Umwandeln eines Angebots ist der Kunde längst bekannt.
        """
        super().__init__(verbindung)
        self.art = art
        self.angaben: dict[str, str | int | None] = angaben or {}
        self.positionen: list[dict[str, str | float | int | None]] = positionen or []
        self.direkt = direkt
        self._titel = "Angebot" if art == "angebot" else "Rechnung"

    def inhalt(self) -> ComposeResult:
        """Baut die Auswahl des Kunden.

        Yields:
            Die Kindelemente.
        """
        yield Static(
            f"{self._titel} — Schritt 1 von 3: Kunde wählen.", classes="hinweis"
        )
        kunden = dateien.kunden(self.db, nur_aktive=True)
        if not kunden:
            yield Static(
                "Es gibt noch keine Kunden. Lege zuerst einen an.",
                classes="hinweis",
            )
            return

        punkte = tuple(
            (
                str(kunde["id"]),
                str(nummer),
                kunde["firma"],
                kunde["ansprechpartner"] or "",
            )
            for nummer, kunde in enumerate(kunden, start=1)
        )
        yield Auswahl(punkte, self.kunde_gewaehlt)

    def start_fokus(self) -> None:
        """Springt direkt zur Kontrolle, wenn Kunde und Positionen da sind.

        Beim Umwandeln eines Angebots gibt es nichts zu wählen: Der Kunde
        steht fest, die Positionen sind übernommen. Es fehlen nur Nummer,
        Datum und Fälligkeit.
        """
        if self.direkt and self.angaben.get("kunde_id"):
            self.app.push_screen(KontrolleScreen(self.db, self.art, self))
            return
        auswahl = self.query(Auswahl)
        if auswahl:
            auswahl.first().focus()

    def kunde_gewaehlt(self, kunde_id: str) -> None:
        """Weiter zu den Positionen.

        Args:
            kunde_id: Die Nummer des gewählten Kunden.
        """
        self.angaben["kunde_id"] = int(kunde_id)
        self.app.push_screen(PositionenScreen(self.db, self.art, self))

    def _vorschlag(self, feld: str) -> str:
        """Baut den Vorschlag für ein Feld.

        Args:
            feld: Der Name des Feldes.

        Returns:
            Der Vorschlag als Text. Datum und Termin sind rechenbar, die
            Notiz bekommt keinen.
        """
        if feld == "datum":
            return betraege.heute()
        if feld == "faellig":
            return betraege.plus_tage(14)
        if feld == "gueltig_bis":
            return betraege.plus_tage(21)
        if feld == "nummer":
            return dateien.naechste_nummer(self.db)
        return ""


class PositionenScreen(BasisScreen):
    """Die Positionen eines Dokuments sammeln."""

    def __init__(
        self,
        verbindung: sqlite3.Connection,
        art: str,
        eltern: EditorScreen,
    ) -> None:
        """Legt den Bildschirm an.

        Args:
            verbindung: Die Datenbankverbindung.
            art: ``angebot`` oder ``rechnung``.
            eltern: Der Editor, in den die Positionen zurückgegeben werden.
        """
        super().__init__(verbindung)
        self.art = art
        self.eltern = eltern
        self.positionen = list(eltern.positionen)

    async def on_screen_resume(self) -> None:
        """Baut die Liste neu auf, wenn eine Position dazu kam.

        Der Inhalt entsteht beim Öffnen. Ohne Neubau stünde hier noch die
        leere Liste, nach der man eine Position hinzugefügt hat.
        """
        await self.recompose()
        self.call_after_refresh(self.start_fokus)

    def inhalt(self) -> ComposeResult:
        """Baut die Liste der Positionen.

        Yields:
            Die Kindelemente.
        """
        summe = sum(
            betraege.zahl(p.get("menge", 1.0)) * betraege.zahl(p.get("preis", 0.0))
            for p in self.positionen
        )
        yield Static(
            "Schritt 2 von 3: Positionen. "
            f"{len(self.positionen)} Positionen, {betraege.euro(summe)}",
            classes="hinweis",
        )
        yield Static("", classes="abstand")

        punkte: list[tuple[str, str, str, str]] = [
            self._als_punkt(nummer, position)
            for nummer, position in enumerate(self.positionen, start=1)
        ]
        punkte.append(
            (
                "neu",
                "+",
                "Position aus der Preisliste",
                "Eine Leistung hinzufügen",
            )
        )
        punkte.append(
            (
                "rabatt",
                "%",
                "Rabatt eintragen",
                "Einen festen Betrag abziehen",
            )
        )
        punkte.append(("fertig", "⏎", "Fertig", "Weiter zur Kontrolle"))

        yield Auswahl(tuple(punkte), self.gewaehlt)

    @staticmethod
    def _als_punkt(
        nummer: int, position: dict[str, str | float | int | None]
    ) -> tuple[str, str, str, str]:
        """Baut aus einer Position einen Punkt für die Liste.

        Args:
            nummer: Die laufende Nummer der Position.
            position: Die Position aus dem Dokument.

        Returns:
            Der Punkt als Schlüssel, Nummer, Bezeichnung, Erläuterung.
        """
        menge = betraege.menge(betraege.zahl(position.get("menge", 1.0)))
        einheit = str(position.get("einheit", ""))
        preis = betraege.euro(betraege.zahl(position.get("preis", 0.0)))
        beschreibung = f"{menge} {einheit} × {preis}"
        return (
            f"p{nummer}",
            str(nummer),
            str(position.get("bezeichnung", "")),
            beschreibung,
        )

    def gewaehlt(self, aktion: str) -> None:
        """Reagiert auf die Auswahl.

        Args:
            aktion: Der Schlüssel des gewählten Punktes.
        """
        if aktion == "fertig":
            if not self.positionen:
                self.meldung("Ohne Positionen gibt es nichts zu rechnen.", gut=False)
                return
            self.eltern.positionen = self.positionen
            self.app.push_screen(KontrolleScreen(self.db, self.art, self.eltern))
        elif aktion == "neu":
            self.app.push_screen(
                LeistungAuswahlScreen(self.db, self.art, self._position_gesetzt)
            )
        elif aktion == "rabatt":
            self.app.push_screen(RabattScreen(self.db, self._rabatt_gesetzt))
        elif aktion.startswith("p"):
            nummer = int(aktion[1:]) - 1
            self.app.push_screen(
                FreiePositionScreen(self.db, self.art, self._position_geaendert, nummer)
            )

    def _rabatt_gesetzt(self, betrag: float, bezeichnung: str) -> None:
        """Nimmt den Rabatt als Position auf.

        Springt nicht selbst zurück: :class:`RabattScreen` räumt sich ab,
        sobald es den Betrag durchgegeben hat. Zwei Pops für einen Push
        kämen einen Bildschirm zu weit zurück.

        Args:
            betrag: Der Betrag als positiver Wert, etwa ``300``.
            bezeichnung: Die Bezeichnung auf dem Dokument.
        """
        self.positionen.append(
            {
                "leistung_id": None,
                "bezeichnung": bezeichnung,
                "menge": 1,
                "einheit": "",
                "preis": -abs(betrag),
            }
        )
        self.eltern.positionen = self.positionen

    def _position_gesetzt(self, position: dict[str, str | float | int | None]) -> None:
        """Nimmt eine neue Position auf.

        Args:
            position: Die Position.
        """
        self.positionen.append(position)
        self.eltern.positionen = self.positionen
        self.app.pop_screen()

    def _position_geaendert(
        self, position: dict[str, str | float | int | None], nummer: int
    ) -> None:
        """Ersetzt eine Position.

        Args:
            position: Die Position.
            nummer: Der Index in der Liste.
        """
        self.positionen[nummer] = position
        self.eltern.positionen = self.positionen
        self.app.pop_screen()


class LeistungAuswahlScreen(BasisScreen):
    """Eine Leistung aus der Preisliste für das Dokument wählen."""

    def __init__(
        self,
        verbindung: sqlite3.Connection,
        art: str,
        fertig: object,
    ) -> None:
        """Legt den Bildschirm an.

        Args:
            verbindung: Die Datenbankverbindung.
            art: ``angebot`` oder ``rechnung``.
            fertig: Wird mit der gewählten Position aufgerufen.
        """
        super().__init__(verbindung)
        self.art = art
        self.fertig = fertig
        self.leistungen = dateien.leistungen(verbindung, nur_aktive=True)

    def inhalt(self) -> ComposeResult:
        """Baut die Liste der Leistungen.

        Yields:
            Die Kindelemente.
        """
        yield Static(
            "Welche Leistung soll auf das Dokument? esc geht zurück.",
            classes="hinweis",
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
        """Legt den Fokus auf die Liste der Leistungen."""
        self.query_one(Tabelle).focus()

    def on_tabelle_gewaehlt(self, event: Tabelle.Gewaehlt) -> None:
        """Fragt nach der Menge und übernimmt die Leistung.

        Args:
            event: Die Nachricht der Tabelle.
        """
        if event.zeile >= len(self.leistungen):
            return

        leistung = self.leistungen[event.zeile]
        self.app.push_screen(
            FreiePositionScreen(
                self.db,
                self.art,
                self._uebernommen,
                None,
                start={
                    "leistung_id": leistung["id"],
                    "bezeichnung": leistung["bezeichnung"],
                    "beschreibung": leistung["beschreibung"],
                    "einheit": leistung["einheit"],
                    "menge": "1",
                    "preis": betraege.euro(leistung["preis"]).replace(" €", ""),
                },
            )
        )

    def _uebernommen(
        self, position: dict[str, str | float | int | None], _nummer: int | None
    ) -> None:
        """Übernimmt die fertige Position.

        Args:
            position: Die Position.
            _nummer: Ungenutzt, die Leistung wird immer angehängt.
        """
        self.fertig(position)
        self.app.pop_screen()


class RabattScreen(BasisScreen):
    """Einen festen Rabattbetrag eintragen.

    Gefragt wird nur der Betrag. Das Vorzeichen wird selbst gesetzt, weil
    ein Rabatt immer abzieht. Die Bezeichnung bleibt "Rabatt" und ist
    aenderbar, falls auf dem Dokument etwas anderes stehen soll.
    """

    #: Die Beschriftung, die auf dem Dokument steht.
    BEZEICHNUNG = "Rabatt"

    def __init__(
        self,
        verbindung: sqlite3.Connection,
        fertig: Callable[[float, str], None],
    ) -> None:
        """Legt den Bildschirm an.

        Args:
            verbindung: Die Datenbankverbindung.
            fertig: Wird mit Betrag und Bezeichnung aufgerufen.
        """
        super().__init__(verbindung)
        self.fertig = fertig

    def inhalt(self) -> ComposeResult:
        """Baut das Formular.

        Yields:
            Die Kindelemente.
        """
        yield Static(
            "Der Betrag wird abgezogen, das Minus setzt das Programm.",
            classes="hinweis",
        )
        yield Formular(
            [
                ("betrag", "Rabatt", "300,00"),
                ("bezeichnung", "Bezeichnung", self.BEZEICHNUNG),
            ]
        )

    def start_fokus(self) -> None:
        """Legt den Cursor ins Betragsfeld."""
        self.query_one(Formular).focus_first()

    def on_formular_fertig(self, event: Formular.Fertig) -> None:
        """Gibt Betrag und Bezeichnung nach oben.

        Args:
            event: Die Nachricht des Formulars.
        """
        betrag = betraege.zahl(event.werte.get("betrag"))

        if betrag == 0:
            self.meldung("Ohne Betrag waere das kein Rabatt.", gut=False)
            return

        bezeichnung = event.werte.get("bezeichnung", "").strip() or self.BEZEICHNUNG
        self.fertig(betrag, bezeichnung)
        self.app.pop_screen()

    def on_formular_verloren(self) -> None:
        """Geht zurueck, ohne zu speichern."""
        self.app.pop_screen()


class FreiePositionScreen(BasisScreen):
    """Eine Position von Hand eintragen.

    Wird benutzt, wenn etwas auf das Dokument soll, das nicht in der
    Preisliste steht.
    """

    def __init__(
        self,
        verbindung: sqlite3.Connection,
        art: str,
        fertig: object,
        nummer: int | None,
        start: dict[str, str] | None = None,
    ) -> None:
        """Legt den Bildschirm an.

        Args:
            verbindung: Die Datenbankverbindung.
            art: ``angebot`` oder ``rechnung``.
            fertig: Wird mit der Position und dem Index aufgerufen.
            nummer: Der Index der Position, die geändert wird, sonst ``None``.
            start: Werte, die schon drinstehen.
        """
        super().__init__(verbindung)
        self.art = art
        self.fertig = fertig
        self.nummer = nummer
        self.start = start or {}

    def inhalt(self) -> ComposeResult:
        """Baut das Formular.

        Yields:
            Die Kindelemente.
        """
        werte = {
            "bezeichnung": self.start.get("bezeichnung", ""),
            "menge": self.start.get("menge", "1"),
            "einheit": self.start.get("einheit", ""),
            "preis": self.start.get("preis", ""),
        }
        yield Formular(
            [
                ("bezeichnung", "Bezeichnung", ""),
                ("menge", "Menge", "1"),
                ("einheit", "Einheit", "Stunde"),
                ("preis", "Preis", "0,00"),
            ],
            werte,
        )
        yield Static(f"Gesamt: {self._summe_aus(werte)}", id="positionssumme")

    def _summe_aus(self, werte: dict[str, str]) -> str:
        """Rechnet die Summe aus den Werten des Formulars.

        Args:
            werte: Die Werte.

        Returns:
            Die Summe als Text.
        """
        menge = betraege.zahl(werte.get("menge", "1"))
        preis = betraege.zahl(werte.get("preis", "0"))
        return betraege.euro(menge * preis)

    def start_fokus(self) -> None:
        """Legt den Cursor ins erste Feld."""
        self.query_one(Formular).focus_first()

    def on_input_changed(self, event: object) -> None:
        """Rechnet die Summe bei jeder Eingabe neu.

        Args:
            event: Das Ereignis von Textual.
        """
        werte = self.query_one(Formular).werte()
        self.query_one("#positionssumme", Static).update(
            f"Gesamt: {self._summe_aus(werte)}"
        )

    def on_formular_fertig(self, event: Formular.Fertig) -> None:
        """Gibt die Position zurück.

        Args:
            event: Die Nachricht des Formulars.
        """
        if not event.werte.get("bezeichnung"):
            self.meldung("Ohne Bezeichnung geht es nicht.", gut=False)
            return

        position: dict[str, str | float | int | None] = {
            "leistung_id": self.start.get("leistung_id"),
            "bezeichnung": event.werte["bezeichnung"],
            "menge": betraege.zahl(event.werte.get("menge") or "1"),
            "einheit": event.werte.get("einheit", ""),
            "preis": betraege.zahl(event.werte.get("preis")),
        }
        self.fertig(position, self.nummer)

    def on_formular_verloren(self) -> None:
        """Geht zurück, ohne zu speichern."""
        self.app.pop_screen()


class KontrolleScreen(BasisScreen):
    """Die letzte Kontrolle vor dem Speichern."""

    def __init__(
        self,
        verbindung: sqlite3.Connection,
        art: str,
        eltern: EditorScreen,
    ) -> None:
        """Legt den Bildschirm an.

        Args:
            verbindung: Die Datenbankverbindung.
            art: ``angebot`` oder ``rechnung``.
            eltern: Der Editor mit Kopf und Positionen.
        """
        super().__init__(verbindung)
        self.art = art
        self.eltern = eltern

    def inhalt(self) -> ComposeResult:
        """Baut die Zusammenfassung.

        Yields:
            Die Kindelemente.
        """
        felder = KOPFFELDER_ANGEBOT if self.art == "angebot" else KOPFFELDER_RECHNUNG

        # Nummer, Datum und Termin sind rechenbar, die werden eingetragen.
        # Die Notiz bleibt leer, sonst steht auf jedem Dokument ein Text,
        # den niemand geschrieben hat.
        kopf_werte: dict[str, str] = {}
        for name, _beschriftung, _hinweis in felder:
            if name == "notiz":
                continue
            wert = self.eltern.angaben.get(name) or self.eltern._vorschlag(name)
            if wert:
                kopf_werte[name] = str(wert)
        kopf_werte["notiz"] = str(self.eltern.angaben.get("notiz", ""))

        kunde = dateien.kunde_holen(
            self.db, int(self.eltern.angaben.get("kunde_id") or 0)
        )
        summe = sum(
            betraege.zahl(p.get("menge", 1.0)) * betraege.zahl(p.get("preis", 0.0))
            for p in self.eltern.positionen
        )

        yield Static(
            "Schritt 3 von 3: Kontrolle. Enter speichert und schreibt die PDF.",
            classes="hinweis",
        )
        yield Static("", classes="abstand")
        yield Static(
            f"{'Angebot' if self.art == 'angebot' else 'Rechnung'} "
            f"{self.eltern.angaben.get('nummer', '')}",
            classes="detail_titel",
        )
        yield Static(
            f"an {kunde['firma'] if kunde else 'unbekannt'}", classes="detail_zeile"
        )
        yield Static("", classes="abstand")

        for position in self.eltern.positionen:
            zeile = (
                f"  {position['bezeichnung'][:38]:<40}"
                f"{betraege.menge(betraege.zahl(position.get('menge', 1.0))):>5}"
                f" {str(position.get('einheit', ''))[:8]:<9}"
                f"{betraege.euro(betraege.zahl(position.get('preis', 0.0))):>12}"
            )
            yield Static(zeile, classes="detail_zeile")

        yield Static("", classes="abstand")
        yield Static(f"Gesamtbetrag    {betraege.euro(summe)}", classes="summe_wert")
        yield Static("", classes="abstand")
        yield Formular(felder, kopf_werte)

    def start_fokus(self) -> None:
        """Legt den Fokus ins erste Feld des Kopfs."""
        self.query_one(Formular).focus_first()

    def on_formular_fertig(self, event: Formular.Fertig) -> None:
        """Speichert das Dokument und schreibt die PDF.

        Args:
            event: Die Nachricht des Formulars.
        """
        angaben = dict(self.eltern.angaben)
        angaben.update(event.werte)

        if not angaben.get("nummer"):
            self.meldung("Ohne Nummer geht es nicht.", gut=False)
            return

        nummer = str(angaben["nummer"]).strip()
        if nummer in dateien.nummern(self.db):
            self.meldung(f"Die Nummer {nummer} ist schon vergeben.", gut=False)
            return

        art = self.art
        dokument_id = dateien.dokument_speichern(
            self.db,
            {"art": art, **angaben},
            self.eltern.positionen,
        )

        dokument = dateien.dokument_holen(self.db, dokument_id)
        if dokument is None:
            self.meldung("Das Dokument liess sich nicht lesen.", gut=False)
            return

        ziel = db.ausgabeordner() / f"{dateiname(dokument, art)}.pdf"
        try:
            pdf.erzeugen(self.db, dokument, ziel)
        except OSError:
            self.hinweis("Gespeichert, aber ohne PDF.", gut=False)
            self.app.pop_screen()
            return

        self.app.pop_screen()
        self.app.pop_screen()
        self.hinweis(f"Gespeichert: {ziel}")
