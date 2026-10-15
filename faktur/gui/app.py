"""Der Start der Fenster-Oberfläche.

Der Rahmen um alles: die Anwendung, die Farben, das Fensterbild.

**Bewusst wenig Eigenes.** Qt holt sich die Darstellung vom System: die
Farben, die Schrift, die Rahmendicke, das Verhalten der Menüs. Was hier
steht, sind nur drei Trennlinien und eine graue Zweitzeile. Alles andere
nimmt der Systemstil mit — auf dem Mac dessen Glas, auf Linux dessen
Thema. Wer hier Farben festsetzt, macht das Programm auf beiden Systemen
fremd.
"""

from __future__ import annotations

import faulthandler
import sqlite3
import sys
from pathlib import Path

from faktur import __version__

__all__ = ["main"]

#: Drei Linien und eine graue Zweitzeile. Sonst nichts.
#:
#: ``palette(mid)`` ist der Systemwert, keine Zahl. Er passt sich an das
#: helle wie an das dunkle Thema an, und darum ist es eine Zahl in keinem
#: Fall.
#:
#: **Keine Farben für Flächen, keine für Auswahl, keine für Schrift.** Qt
#: holt sich die vom System, und auf dem Mac dessen Glas. Wer sie hier
#: festsetzt, macht das Programm auf beiden Systemen fremd — und die
#: Oberfläche sähe auf macOS aus wie ein Windows-Programm.
_STYLE = """
#leiste {
    background: transparent;
    border: none;
}

#tabelle {
    background: transparent;
    border: none;
    alternate-background-color: palette(alternate-base);
}

/* Die graue Zweitzeile.

   **Nicht ``palette(mid)``.** Auf diesem System ist Mid genau die
   Hintergrundfarbe — der Text waere unsichtbar. ``palette(dark)`` hebt
   sich von Window und Base ab und bleibt es auf dem Mac im hellen wie im
   dunklen Thema. */
#suchzeile, #zweit {
    color: palette(dark);
}

/* Der Kasten auf der Übersicht. Nur Systemfarben, damit er auf dem Mac
   dessen Fensterfarbe nimmt und auf Linux die des Linux-Themas. */
#hinweis {
    background: palette(base);
    border: 1px solid palette(mid);
    border-radius: 8px;
}

/* Die eine Taste, um die es geht. Nur fett — eine eigene Farbe sähe
   auf dem Mac aus wie ein Fremdkörper. */
#haupt {
    font-weight: bold;
}
"""


def _kaputt_erzählt() -> None:
    """Lässt sich einen Absturz auf der Konsole ausgeben.

    Ohne das endet ein Absturz in der GUI in einem Fenster, in dem nichts
    steht. Ein Traceback auf der Konsole kann man lesen und weitergeben.

    Returns:
        Nichts.
    """
    import traceback

    def zeige(typ: object, wert: object, spur: object) -> None:
        traceback.print_exception(typ, wert, spur)  # type: ignore[arg-type]

    sys.excepthook = zeige  # type: ignore[assignment]


def main(argv: list[str] | None = None) -> int:
    """Öffnet das Fenster und wartet, bis es geschlossen wird.

    Args:
        argv: Die Argumente. Ohne Angabe die des Programms.

    Returns:
        Der Rückgabewert von Qt.
    """
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:  # pragma: no cover - nur ohne PySide6
        sys.stderr.write(
            "PySide6 fehlt. Bitte einmal ./start.sh laufen lassen, das holt "
            "die Bibliotheken nach.\n"
        )
        return 1

    faulthandler.enable()
    _kaputt_erzählt()

    from faktur.gui.fenster import Fenster

    app = QApplication.instance() or QApplication(
        argv if argv is not None else sys.argv
    )
    app.setApplicationName("Faktur")
    app.setApplicationDisplayName("Faktur")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("New Air Media Group")
    app.setOrganizationDomain("newairmedia.de")
    app.setStyleSheet(_STYLE)

    bild = _bild()
    if bild is not None:
        from PySide6.QtGui import QIcon

        app.setWindowIcon(QIcon(str(bild)))

    fenster = Fenster(_verbindung())
    fenster.zeige()

    return app.exec()


def _verbindung() -> sqlite3.Connection:
    """Öffnet die Datenbank neben dem Programm.

    Returns:
        Die offene Verbindung.
    """
    from faktur import db

    return db.verbinden()


def _bild() -> Path | None:
    """Sucht das Fensterbild.

    Returns:
        Der Pfad zum Bild, oder ``None``, wenn keins da ist.
    """
    hier = Path(__file__).resolve().parents[2]
    for name in ("assets/icon.png", "daten/logo.png"):
        kandidat = hier / name
        if kandidat.is_file():
            return kandidat
    return None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
