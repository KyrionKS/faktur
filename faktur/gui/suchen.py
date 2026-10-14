"""Das Suchfeld und die Zeile, die zählt.

Zwei kleine Bausteine, die jede Liste im Fenster hat. Sie gehören
zusammen, weil sie dasselbe erzählen: *wie viele Zeilen bleiben übrig*.

Das Filtern selbst steht in :mod:`faktur.suchen`. Hier passiert nichts
außer Anzeigen und Melden — sonst hätte man das Suchverhalten an zwei
Stellen.
"""

from __future__ import annotations

from faktur.gui.qt import QLabel, QLineEdit

#: Der Text, solange nichts getippt ist.
_PLATZHALTER = "Suchen"


class Suchfeld(QLineEdit):
    """Ein Eingabefeld, das sofort filtert.

    Es meldet jede Änderung an die Liste, ohne dass man etwas bestätigen
    muss. Bei zwanzig Kunden ist ein Dialog lästig; bei zweihundert ist die
    Liste ohne Suchfeld unbrauchbar.

    Attributes:
        geaendert: Wird mit dem aktuellen Begriff gerufen.
    """

    def __init__(self, geaendert: object, platzhalter: str = _PLATZHALTER) -> None:
        """Legt das Feld an.

        Args:
            geaendert: Wird gerufen, sobald sich der Text ändert.
            platzhalter: Der Text, solange nichts getippt ist.
        """
        super().__init__()
        self.setObjectName("suche")
        self.setPlaceholderText(platzhalter)
        self.setClearButtonEnabled(True)
        self.neaendert = geaendert
        self.textChanged.connect(self._geaendert)

    def _geaendert(self, text: str) -> None:
        """Reicht den neuen Begriff weiter.

        Args:
            text: Der neue Text.

        Returns:
            Nichts.
        """
        self.neaendert(text)  # type: ignore[operator]

    def leeren(self) -> None:
        """Leert das Feld und sucht wieder alles.

        Returns:
            Nichts.
        """
        self.clear()

    def keyPressEvent(self, event: object) -> None:  # noqa: N802
        """Behandelt das Escape-Zeichen.

        Args:
            event: Das Tastenereignis.

        Returns:
            Nichts.
        """
        from faktur.gui.qt import QKeyEvent

        if (
            isinstance(event, QKeyEvent)
            and event.key() == int(_escape())
            and self.text()
        ):
            self.clear()
            return
        super().keyPressEvent(event)  # type: ignore[arg-type]


class SuchZeile(QLabel):
    """Die Zeile, die sagt, wie viele Zeilen übrig sind."""

    def zeige(
        self,
        gefunden: int,
        gesamt: int,
        begriff: str,
        einheit: str = "Einträge",
        einzeln: str = "Eintrag",
    ) -> None:
        """Sagt an, wie viel die Suche übrig gelassen hat.

        Ohne Suchbegriff steht dort einfach, wie viele es gibt. Bei null
        Treffern steht das ausdrücklich da — eine leere Liste sieht sonst
        aus, als sei das Programm kaputt.

        Args:
            gefunden: Wie viele Zeilen passen.
            gesamt: Wie viele es insgesamt gab.
            begriff: Was gesucht wurde.
            einheit: Die Pluralform, zum Beispiel *Dokumente*.
            einzeln: Die Singularform, zum Beispiel *Dokument*.
        """
        if not begriff.strip():
            self.setText(f"{gesamt} {einzeln if gesamt == 1 else einheit}")
            return

        if gefunden == 0:
            self.setText(f"{gesamt} gefunden. Nichts passt zu „{begriff}“")
        elif gefunden < gesamt:
            self.setText(f"{gefunden} von {gesamt} passen zu „{begriff}“")
        else:
            self.setText(f"Alle {gesamt} passen zu „{begriff}“")


def _escape() -> object:
    """Gibt die Escape-Taste zurück.

    Returns:
        Die Taste.
    """
    from faktur.gui.qt import Qt

    return Qt.Key.Key_Escape
