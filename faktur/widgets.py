"""Eigene Bausteine der Oberfläche.

Das Logo, die Auswahlliste mit den Pfeiltasten, das Formular für die Felder,
die Tabelle für Kunden und Leistungen und die Meldungszeile am unteren
Rand. Alle so, dass sie sich gleich verhalten und gleich aussehen.
"""

from __future__ import annotations

from collections.abc import Callable

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Input, Label, Static

from faktur import zeichen

#: Die Akzentfarbe, aus dem Logo ausgelesen.
AKZENT = "#512E80"

#: Ein hellerer Ton derselben Farbe, für Spaltenköpfe und Nummern.
AKZENT_HELL = "#9C7FC7"

#: Der Pfeil vor dem gewählten Punkt.
PFEIL = "▶"

#: Der Platz, den der Pfeil einnimmt, damit die Spalten nicht springen.
PFEIL_RAUM = "  "


class LogoKopf(Static):
    """Das Logo oben auf jeder Seite.

    Das Gitter aus :mod:`faktur.zeichen` wird in der Akzentfarbe gezeichnet,
    der Firmenname steht rechts daneben. Auf einem sehr hohen Terminal
    reicht der Firmenname allein.
    """

    def render(self) -> Text:
        """Zeichnet das Logo.

        Returns:
            Der Text für die Anzeige.
        """
        hoehe = self.app.size.height if self.app else 24
        return Text(zeichen.kopf_text(hoehe), style=f"bold {AKZENT}")


class Auswahl(Static):
    """Eine Liste, die man mit den Pfeiltasten bewegt.

    Jeder Punkt besteht aus einem Schlüssel, einer Nummer, einem Titel und
    einer kurzen Erklärung. Nummer und Titel stehen links, die Erklärung in
    einer eigenen Spalte, so wie in ``beispiel.png``.
    """

    BINDINGS = [
        Binding("up", "hoch", "Hoch", show=False),
        Binding("down", "runter", "Runter", show=False),
        Binding("home", "anfang", "Nach oben", show=False),
        Binding("end", "ende", "Nach unten", show=False),
        Binding("enter,space", "waehlen", "Wählen", show=False),
    ]

    can_focus = True

    def __init__(
        self,
        punkte: tuple[tuple[str, str, str, str], ...],
        gewaehlt: Callable[[str], None],
    ) -> None:
        """Legt die Liste an.

        Args:
            punkte: Die Punkte als Schlüssel, Nummer, Titel, Erklärung.
            gewaehlt: Wird mit dem Schlüssel des gewählten Punktes gerufen.
        """
        super().__init__()
        self.punkte = punkte
        self.gewaehlt = gewaehlt
        self.index = 0
        self.add_class("auswahl")

    def render(self) -> Text:
        """Zeichnet die Liste.

        Returns:
            Der Text für die Anzeige.
        """
        text = Text()
        for nummer, (_schluessel, taste, titel, erklaerung) in enumerate(
            self.punkte, start=1
        ):
            gewaehlt = nummer - 1 == self.index
            zeile = Text()

            if gewaehlt:
                zeile.append(PFEIL + " ", style=f"bold {AKZENT}")
            else:
                zeile.append(PFEIL_RAUM)

            zeile.append(f"{taste:>2}. ", style=f"bold {AKZENT_HELL}")
            zeile.append(f"{titel:<24} ", style=f"bold {AKZENT}" if gewaehlt else "")
            zeile.append(f" {erklaerung}", style="" if gewaehlt else "dim")
            zeile.append("\n")

            text.append(zeile)
        return text

    def _bewege(self, schritt: int) -> None:
        """Bewegt den Cursor, ohne über die Enden hinaus.

        Args:
            schritt: Wie viele Plätze vor oder zurück.
        """
        anzahl = len(self.punkte)
        if anzahl:
            self.index = max(0, min(self.index + schritt, anzahl - 1))
            self.refresh()

    def action_hoch(self) -> None:
        """Geht einen Punkt nach oben."""
        self._bewege(-1)

    def action_runter(self) -> None:
        """Geht einen Punkt nach unten."""
        self._bewege(1)

    def action_anfang(self) -> None:
        """Springt nach oben."""
        self.index = 0
        self.refresh()

    def action_ende(self) -> None:
        """Springt nach unten."""
        self.index = max(0, len(self.punkte) - 1)
        self.refresh()

    def action_waehlen(self) -> None:
        """Bestätigt den markierten Punkt."""
        if self.punkte:
            self.gewaehlt(self.punkte[self.index][0])

    def on_key(self, event: object) -> None:
        """Sucht Punkte über Nummer und Anfangsbuchstabe.

        Args:
            event: Das Tastenereignis von Textual.
        """
        taste = getattr(event, "key", "")
        if not taste or len(taste) != 1:
            return

        gesucht = taste.lower()
        for nummer, (_schluessel, taste_text, titel, _erklaerung) in enumerate(
            self.punkte
        ):
            if taste_text.lower() == gesucht or titel.lower().startswith(gesucht):
                self.index = nummer
                self.refresh()
                event.stop()
                self.action_waehlen()
                return


class Tabelle(Static):
    """Eine Liste von Zeilen mit Spalten.

    Der Benutzer bewegt sich mit den Pfeiltasten, bestätigt mit ``Enter``
    und ändert mit ``F2``.
    """

    BINDINGS = [
        Binding("up", "hoch", "Hoch", show=False),
        Binding("down", "runter", "Runter", show=False),
        Binding("enter", "waehlen", "Öffnen", show=True),
        Binding("f2", "bearbeiten", "Ändern", show=True),
        Binding("delete", "loeschen", "Löschen", show=True),
    ]

    can_focus = True

    class Bearbeiten(Message):
        """Wird gesendet, wenn eine Zeile geändert werden soll.

        Attributes:
            zeile: Der Index der Zeile.
        """

        def __init__(self, zeile: int) -> None:
            """Legt die Nachricht an.

            Args:
                zeile: Der Index der Zeile.
            """
            super().__init__()
            self.zeile = zeile

    class Loeschen(Message):
        """Wird gesendet, wenn eine Zeile weg soll.

        Attributes:
            zeile: Der Index der Zeile.
        """

        def __init__(self, zeile: int) -> None:
            """Legt die Nachricht an.

            Args:
                zeile: Der Index der Zeile.
            """
            super().__init__()
            self.zeile = zeile

    class Gewaehlt(Message):
        """Wird gesendet, wenn eine Zeile bestätigt wird.

        Attributes:
            zeile: Der Index der Zeile.
        """

        def __init__(self, zeile: int) -> None:
            """Legt die Nachricht an.

            Args:
                zeile: Der Index der Zeile.
            """
            super().__init__()
            self.zeile = zeile

    def __init__(
        self,
        spalten: list[tuple[str, int]],
        zeilen: list[list[str]],
    ) -> None:
        """Legt die Tabelle an.

        Args:
            spalten: Die Spalten als Titel und Breite in Buchstaben.
            zeilen: Die Inhalte, je Zeile eine Liste von Texten.
        """
        super().__init__()
        self.spalten = spalten
        self.zeilen = zeilen
        self.index = 0
        self.add_class("tabelle")

    def _zelle(self, inhalt: str, spalte: int) -> str:
        """Kürzt oder ergänzt einen Text auf die Spaltenbreite.

        Args:
            inhalt: Der Text.
            spalte: Der Index der Spalte.

        Returns:
            Der Text in voller Spaltenbreite.
        """
        breite = self.spalten[spalte][1]
        if len(inhalt) > breite:
            return inhalt[: breite - 1] + "…"
        return inhalt.ljust(breite)

    def render(self) -> Text:
        """Zeichnet Kopf und Zeilen.

        Returns:
            Der Text für die Anzeige.
        """
        kopf = Text(PFEIL_RAUM)
        for titel, breite in self.spalten:
            kopf.append(titel.ljust(breite) + " ", style=f"bold {AKZENT_HELL}")
        kopf.append("\n")

        text = Text()
        if not self.zeilen:
            text.append("\n  Nichts vorhanden.\n", style="dim")
            return kopf + text

        for nummer, zellen in enumerate(self.zeilen):
            gewaehlt = nummer == self.index
            stil = f"bold {AKZENT}" if gewaehlt else ""
            text.append(PFEIL + " " if gewaehlt else PFEIL_RAUM + " ")
            for spalte, zelle in enumerate(zellen):
                text.append(self._zelle(zelle, spalte), style=stil)
                text.append(" ")
            text.append("\n")

        return kopf + text

    def _bewege(self, schritt: int) -> None:
        """Bewegt den Cursor durch die Zeilen.

        Args:
            schritt: Wie viele Zeilen vor oder zurück.
        """
        if self.zeilen:
            self.index = max(0, min(self.index + schritt, len(self.zeilen) - 1))
            self.refresh()

    def _markiert(self) -> int | None:
        """Gibt den Index der markierten Zeile zurück.

        Returns:
            Der Index, oder ``None``, wenn die Tabelle leer ist.
        """
        return self.index if self.zeilen else None

    def action_hoch(self) -> None:
        """Geht eine Zeile nach oben."""
        self._bewege(-1)

    def action_runter(self) -> None:
        """Geht eine Zeile nach unten."""
        self._bewege(1)

    def action_waehlen(self) -> None:
        """Bestätigt die markierte Zeile."""
        zeile = self._markiert()
        if zeile is not None:
            self.post_message(self.Gewaehlt(zeile))

    def action_bearbeiten(self) -> None:
        """Will die markierte Zeile ändern."""
        zeile = self._markiert()
        if zeile is not None:
            self.post_message(self.Bearbeiten(zeile))

    def action_loeschen(self) -> None:
        """Will die markierte Zeile löschen."""
        zeile = self._markiert()
        if zeile is not None:
            self.post_message(self.Loeschen(zeile))


class Formular(Vertical):
    """Ein Formular aus mehreren Feldern.

    ``Tab`` und ``Shift+Tab`` wechseln das Feld, ``Enter`` speichert am Ende
    des Formulars und geht sonst weiter. ``!`` bricht ab, ohne zu fragen.
    """

    BINDINGS = [
        Binding("!", "verwerfen", "Abbrechen", show=False),
    ]

    class Fertig(Message):
        """Wird gesendet, wenn alle Felder ausgefüllt sind.

        Attributes:
            werte: Die Werte je Feldname.
        """

        def __init__(self, werte: dict[str, str]) -> None:
            """Legt die Nachricht an.

            Args:
                werte: Die Werte je Feldname.
            """
            super().__init__()
            self.werte = werte

    class Verloren(Message):
        """Wird gesendet, wenn der Benutzer mit ``!`` abbricht."""

    def __init__(
        self,
        felder: list[tuple[str, str, str]],
        werte: dict[str, str] | None = None,
    ) -> None:
        """Legt das Formular an.

        Args:
            felder: Die Felder als Name, Beschriftung, Hinweis.
            werte: Die Werte, die wirklich drinstehen. Was hier fehlt,
                bleibt leer — ein Hinweis ist ein Vorschlag, kein Inhalt.
                Sonst speichert ein neuer Kunde unfreiwillig die Musteradresse.
        """
        super().__init__()
        self.felder = felder
        self.startwerte = werte or {}
        self.add_class("formular")

    def compose(self) -> ComposeResult:
        """Baut die Eingabefelder.

        Yields:
            Die Kindelemente.
        """
        for name, beschriftung, hinweis in self.felder:
            with Horizontal(classes="zeile"):
                yield Label(beschriftung, classes="bezeichnung")
                yield Input(
                    value=self.startwerte.get(name, ""),
                    placeholder=hinweis,
                    id=f"f_{name}",
                )
        with Horizontal(classes="zeile"):
            yield Label("Enter speichert   ! bricht ab", classes="bezeichnung")

    def werte(self) -> dict[str, str]:
        """Liest alle Felder aus.

        Returns:
            Die Werte je Feldname.
        """
        return {
            name: self.query_one(f"#f_{name}", Input).value.strip()
            for name, _, _ in self.felder
        }

    def _eingaben(self) -> list[Input]:
        """Gibt die Eingabefelder in Reihenfolge zurück.

        Returns:
            Die Felder.
        """
        return [self.query_one(f"#f_{name}", Input) for name, _, _ in self.felder]

    def focus_first(self) -> None:
        """Setzt den Cursor in das erste Feld."""
        eingaben = self._eingaben()
        if eingaben:
            eingaben[0].focus()

    def action_verwerfen(self) -> None:
        """Bricht ab, ohne etwas zu speichern."""
        self.post_message(self.Verloren())

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Speichert am letzten Feld, sonst geht es ein Feld weiter.

        Args:
            event: Das Ereignis von Textual.
        """
        event.stop()
        eingaben = self._eingaben()
        if not eingaben:
            return

        if event.input is eingaben[-1]:
            self.post_message(self.Fertig(self.werte()))
        else:
            eingaben[eingaben.index(event.input) + 1].focus()


class Meldung(Static):
    """Eine Zeile am unteren Rand für Hinweise und Fehler."""

    DEFAULT_CSS = """
    Meldung {
        height: 1;
        padding: 0 2;
        color: $text-muted;
    }
    Meldung.gefehler {
        color: $error;
        text-style: bold;
    }
    """

    def __init__(self) -> None:
        """Legt die Meldungszeile an."""
        super().__init__("")
        self.add_class("meldung")

    def zeige(self, text: str, gut: bool = True) -> None:
        """Schreibt einen Text in die Zeile.

        Args:
            text: Was zu lesen sein soll.
            gut: ``True`` bei Erfolg, ``False`` bei einem Problem.
        """
        self.update(text)
        self.set_class(not gut, "gefehler")
