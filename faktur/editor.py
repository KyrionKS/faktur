"""Der Editor für die Brieftexte.

Angebot und Rechnung haben je einen Text, in dem das Programm Platzhalter
ersetzt. Der Text ist mehrzeilig, weil Absätze durch Leerzeilen getrennt sind.
Ein einzeiliges Eingabefeld kann das nicht: Es klappt alles in eine Zeile
zusammen, und der Text ist so nicht mehr zu bearbeiten.

Darum steht hier ein eigenes Feld mit Zeilennummern. Es verhält sich wie ein
kleiner Texteditor: ``Strg+S`` speichert, ``esc`` bricht ab, Tab fügt
Leerzeichen ein, und der Umbruch ist weich, damit nichts aus dem Bild
verschwindet.
"""

from __future__ import annotations

from collections.abc import Callable

from rich.style import Style
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Label, Static, TextArea
from textual.widgets.text_area import TextAreaTheme

from faktur import einstellungen, texte
from faktur.farben import AKZENT, FEHLER, SEKUNDAER

#: Der Grund, auf dem die Auswahl im Textfeld steht. Etwas aufgehellt,
#: damit man den ausgewählten Absatz noch sieht.
AUSWAHL_GRUND = "#4A3B63"

#: Die Zeile, in der der Cursor steht, etwas aufgehellt.
CURSOR_ZEILE = "#2A2438"

#: Der Name, unter dem das eigene Theme angemeldet wird.
THEMA_NAME = "faktur"

#: Der Text auf der Auswahl. Hell genug gegen den Auswahlgrund.
SELEKTION_TEXT = "#F2ECFA"


class Brieftext(Vertical):
    """Ein mehrzeiliges Textfeld für den Brief.

    Meldet über :class:`Gespeichert`, wenn gespeichert wurde, und über
    :class:`Verloren`, wenn der Benutzer abbricht. Ob die Platzhalter stimmen,
    sagt der Bildschirm danach — ein Tippfehler soll sichtbar bleiben.
    """

    BINDINGS = [
        Binding("ctrl+s", "sichern", "Speichern", show=True),
        Binding("!", "verwerfen", "Abbrechen", show=False),
    ]

    DEFAULT_CSS = """
    Brieftext {
        height: 1fr;
    }
    Brieftext > .hinweis {
        height: auto;
        padding: 0 0 1 0;
    }
    """

    class Gespeichert(Message):
        """Wird gesendet, wenn der Benutzer gespeichert hat.

        Attributes:
            text: Der Text aus dem Feld.
        """

        def __init__(self, text: str) -> None:
            """Legt die Nachricht an.

            Args:
                text: Der Text aus dem Feld.
            """
            super().__init__()
            self.text = text

    class Verloren(Message):
        """Wird gesendet, wenn der Benutzer abbricht."""

    def __init__(
        self,
        text: str,
        beschriftung: str,
        vorschlag: Callable[[], str] | None = None,
        zeilen: int = 14,
    ) -> None:
        """Legt den Editor an.

        Args:
            text: Der Text, der drinsteht.
            beschriftung: Ein Satz darüber, was hier eingetragen wird.
            vorschlag: Liefert den Vorschlag wieder, falls er gebraucht wird.
            zeilen: Wie viele Zeilen das Feld hoch sein soll.
        """
        super().__init__()
        self.vorschlag = vorschlag
        self.add_class("brieftext")

        self.feld = TextArea(
            text,
            soft_wrap=True,
            show_line_numbers=True,
            tab_behavior="indent",
            compact=True,
            id="brief",
        )
        self.feld.styles.height = zeilen

        # ``theme`` nimmt nur den Namen an. Das Theme selbst muss vorher
        # angemeldet werden, sonst sucht Textual nach einem Eintrag mit dem
        # Theme-Objekt als Schlüssel und scheitert daran.
        self.feld.register_theme(self._theme())
        self.feld.theme = THEMA_NAME

        self.beschriftung = beschriftung

    def compose(self) -> ComposeResult:
        """Baut das Feld und die Liste der Platzhalter.

        Yields:
            Die Kindelemente.
        """
        yield Label(self.beschriftung, classes="hinweis")
        yield self.feld
        with VerticalScroll(id="platzhalter"):
            yield Static("Im Text gehen diese Namen:")
            for name, beispiel in einstellungen.PLATZHALTER.items():
                klammern = "{{" + name + "}}"
                yield Static("  " + klammern, classes="platzhalter_name")
                yield Static("      ergibt " + beispiel, classes="platzhalter_wert")

    def _theme(self) -> TextAreaTheme:
        """Baut die Farben des Textfeldes.

        Returns:
            Das Theme in den Markenfarben. Kein Standard-Schwarz auf
            Schwarz, das ist im dunklen Terminal unlesbar.
        """
        return TextAreaTheme(
            name=THEMA_NAME,
            base_style=Style.parse(f"bold {AKZENT}"),
            cursor_style=Style(reverse=True),
            selection_style=Style(bgcolor=AUSWAHL_GRUND, color=SELEKTION_TEXT),
            cursor_line_style=Style(bgcolor=CURSOR_ZEILE),
            gutter_style=Style.parse(f"bold {SEKUNDAER}"),
        )

    def start_fokus(self) -> None:
        """Legt den Cursor an den Anfang des Textes."""
        self.feld.focus()

    @property
    def text(self) -> str:
        """Der Text, der gerade im Feld steht."""
        return self.feld.text

    def sauber(self) -> str:
        """Der Text ohne Leerzeichen am Zeilenende.

        Returns:
            Der Text, wie er in der Datenbank abgelegt wird.
        """
        zeilen = [zeile.rstrip() for zeile in self.feld.text.split("\n")]
        return "\n".join(zeilen).strip()

    def unbekannte(self) -> list[str]:
        """Sucht die Platzhalter, für die es keinen Wert gibt.

        Returns:
            Die Namen in der Reihenfolge des Auftretens.
        """
        return texte.unbekannte(self.sauber())

    def hinweis(self, text: str, fehler: bool = False) -> None:
        """Schreibt einen Satz unter die Überschrift.

        Args:
            text: Was zu lesen sein soll.
            fehler: ``True``, wenn es eine Fehlermeldung ist.
        """
        anzeige = self.query_one(".hinweis", Label)
        anzeige.update(text)
        anzeige.styles.color = FEHLER if fehler else SEKUNDAER

    def vorschlag_einsetzen(self) -> None:
        """Setzt den Vorschlag zurück, falls einer hinterlegt ist."""
        if self.vorschlag is None:
            return
        self.feld.text = self.vorschlag()
        self.feld.move_cursor((0, 0))

    def action_sichern(self) -> None:
        """Schickt den Text nach oben."""
        self.post_message(self.Gespeichert(self.sauber()))

    def action_verwerfen(self) -> None:
        """Bricht ab, ohne zu speichern."""
        self.post_message(self.Verloren())

    def on_key(self, event: object) -> None:
        """Fängt ``esc`` ab, weil das Textfeld die Taste sonst schluckt.

        Args:
            event: Das Tastenereignis von Textual.
        """
        if getattr(event, "key", "") == "escape":
            self.post_message(self.Verloren())
            event.stop()
