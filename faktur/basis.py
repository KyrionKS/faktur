"""Der Rahmen, den alle Bildschirme gemeinsam haben.

Steht hier und nicht in ``faktur.app``, weil die Bildschirme diese Klasse
brauchen und ``faktur.app`` die Bildschirme lädt. Sonst dreht sich der
Import im Kreis.
"""

from __future__ import annotations

import contextlib
import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import Footer, Label

from faktur.widgets import LogoKopf, Meldung


class BasisScreen(Screen[object]):
    """Logo-Kopf, Inhalt, Meldungszeile und Fuß mit den Tasten.

    ``esc`` geht einen Schritt zurück, außer im Hauptmenü. Jeder Bildschirm
    liefert nur seinen Inhalt über :meth:`inhalt`.
    """

    BINDINGS = [
        Binding("escape", "zurueck", "Zurück"),
        Binding("ctrl+q", "beenden", "Beenden"),
    ]

    #: Der Rahmen nimmt keinen Fokus an, sonst schluckt er die Tasten, bevor
    #: die Liste sie sieht.
    can_focus = False

    def __init__(self, verbindung: sqlite3.Connection) -> None:
        """Legt den Bildschirm an.

        Args:
            verbindung: Die Datenbankverbindung.
        """
        super().__init__()
        self.db = verbindung
        #: Was nach einem Ja in einer Frage passieren soll. ``None`` heisst
        #: :meth:`bestaetigt`.
        self._antwort_danach: object = None

    def on_mount(self) -> None:
        """Setzt den Fokus auf das, was bedienbar ist."""
        self.start_fokus()

    def start_fokus(self) -> None:
        """Setzt den Fokus auf das erste bedienbare Element.

        Bildschirme mit einer Liste oder einem Formular überschreiben das.
        """
        from faktur.widgets import Auswahl, Formular, Tabelle

        for typ in (Formular, Tabelle, Auswahl):
            gefunden = self.query(typ)
            if gefunden:
                if isinstance(gefunden.first(), Formular):
                    gefunden.first().focus_first()  # type: ignore[union-attr]
                else:
                    gefunden.first().focus()  # type: ignore[union-attr]
                return

    def compose(self) -> ComposeResult:
        """Baut den Rahmen.

        Yields:
            Die Kindelemente.
        """
        yield LogoKopf()
        with VerticalScroll(id="inhalt") as inhalt:
            # Die Bildlaufleiste ist ein Behaelter, keine Bedienung. Ohne
            # das bekommen ``tab`` und ``shift+tab`` bei jeder Liste einen
            # Zwischenhalt, an dem nichts passiert — auf *Offene
            # Forderungen* musste man ihn zweimal nehmen, um ueberhaupt ins
            # Suchfeld zu kommen.
            inhalt.can_focus = False
            yield from self.inhalt()
        yield Meldung()
        yield Footer()

    def inhalt(self) -> ComposeResult:
        """Der Teil, den jeder Bildschirm selbst liefert.

        Yields:
            Die Kindelemente des Inhalts.
        """
        return iter(())

    def action_zurueck(self) -> None:
        """Geht einen Schritt zurück oder beendet das Programm."""
        if len(self.app.screen_stack) > 1:
            self.app.pop_screen()
        else:
            self.app.exit()

    def action_beenden(self) -> None:
        """Beendet das Programm."""
        self.app.exit()

    def meldung(self, text: str, gut: bool = True) -> None:
        """Zeigt eine Zeile Text auf diesem Bildschirm an.

        Args:
            text: Was zu lesen sein soll.
            gut: ``True`` bei Erfolg, ``False`` bei einem Problem.
        """
        self.query_one(Meldung).zeige(text, gut)

    def hinweis(self, text: str, gut: bool = True) -> None:
        """Zeigt eine Zeile Text auf dem Bildschirm an, der gerade oben ist.

        Wird erst nach dem nächsten Bild aufgerufen. Direkt nach
        ``pop_screen`` oder ``push_screen`` ist der Bildschirm noch nicht
        da, auf dem die Meldung landen soll.

        Args:
            text: Was zu lesen sein soll.
            gut: ``True`` bei Erfolg, ``False`` bei einem Problem.
        """
        self.app.call_after_refresh(self._zeige_hinweis, text, gut)

    def _zeige_hinweis(self, text: str, gut: bool) -> None:
        """Schreibt den aufgeschobenen Hinweis in die Meldungszeile.

        Args:
            text: Was zu lesen sein soll.
            gut: ``True`` bei Erfolg, ``False`` bei einem Problem.
        """
        bildschirm = self.app.screen
        if isinstance(bildschirm, BasisScreen):
            with contextlib.suppress(NoMatches):
                bildschirm.query_one(Meldung).zeige(text, gut)

    def bestaetigen(self, text: str, danach: object = None) -> None:
        """Fragt nach, bevor etwas Endgültiges passiert.

        Args:
            text: Die Frage.
            danach: Wird nach einem Ja aufgerufen. Ohne Angabe wird
                :meth:`bestaetigt` benutzt, wie es seit je war.
        """
        self._antwort_danach = danach
        self.app.push_screen(FrageScreen("Sicher?", text), self._antwort_gekommen)

    def _antwort_gekommen(self, antwort: bool | None) -> None:
        """Macht weiter, wenn der Benutzer bestätigt hat.

        Args:
            antwort: ``True``, wenn ja gewählt wurde.
        """
        danach = self._antwort_danach
        self._antwort_danach = None
        if not antwort:
            return
        if danach is not None:
            danach()  # type: ignore[operator]
        else:
            self.bestaetigt()

    def bestaetigt(self) -> None:
        """Wird aufgerufen, nachdem ja gewählt wurde.

        Bildschirme, bei denen nach dem Löschen etwas passieren soll,
        überschreiben das.
        """


class FrageScreen(Screen[bool]):
    """Ein Fenster mit zwei Möglichkeiten."""

    BINDINGS = [
        Binding("escape,n", "nein", "Abbrechen"),
        Binding("y,j,enter", "ja", "Bestätigen"),
    ]

    def __init__(self, titel: str, text: str) -> None:
        """Legt das Fenster an.

        Args:
            titel: Die Überschrift.
            text: Die Frage.
        """
        super().__init__()
        self.titel = titel
        self.text = text

    def compose(self) -> ComposeResult:
        """Baut das Fenster.

        Yields:
            Die Kindelemente.
        """
        with Vertical(id="fenster"):
            yield Label(self.titel, id="fenster_titel")
            yield Label(self.text, id="fenster_text")
            with Horizontal(id="fenster_knopf"):
                yield Label("Enter  Bestätigen", id="knopf_ja")
                yield Label("esc  Abbrechen", id="knopf_nein")

    def on_mount(self) -> None:
        """Setzt den Fokus auf das Fenster."""
        self.query_one("#fenster").focus()

    def action_ja(self) -> None:
        """Bestätigt."""
        self.dismiss(True)

    def action_nein(self) -> None:
        """Bricht ab."""
        self.dismiss(False)
