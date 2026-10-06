#!/usr/bin/env python3
"""Prüft, ob die Oberfläche auf einem Terminal aufgebaut wird.

Textual kann eine App in einem virtuellen Terminal starten und das Bild
als Text ausgeben. Damit lässt sich ohne Bildschirm prüfen, ob das Menü
vollständig sichtbar ist und die Tasten greifen.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from faktur.app import FakturApp  # noqa: E402


def bild_als_text(app: FakturApp) -> str:
    """Liest das aktuelle Bild aus dem Bildschirmspeicher.

    Args:
        app: Die laufende App.

    Returns:
        Jede Bildschirmzeile, ohne Farbcodes.
    """
    return "\n".join(
        "".join(abschnitt.text for abschnitt in streifen)
        for streifen in app.screen._compositor.render_strips()
    )


async def zeige(breite: int, hoehe: int, befehle: list[str], kopf: str = "") -> str:
    """Startet die App, drückt Tasten und gibt das Bild zurück.

    Args:
        breite: Terminalbreite in Zeichen.
        hoehe: Terminalhöhe in Zeilen.
        befehle: Die Tasten, die nacheinander gedrückt werden.
        kopf: Eine Überschrift für die Ausgabe.

    Returns:
        Das Bild als Text, ohne Farbcodes.
    """
    with tempfile.TemporaryDirectory() as ordner:
        app = FakturApp(Path(ordner) / "test.db")
        async with app.run_test(size=(breite, hoehe)) as pilot:
            await pilot.pause()
            for taste in befehle:
                await pilot.press(taste)
                await pilot.pause()
            return bild_als_text(app)


async def main() -> None:
    """Zeigt das Menü in verschiedenen Terminalgrössen und Zuständen.

    Returns:
        Nichts. Schreibt nach stdout.
    """
    faelle = [
        (80, 24, [], "Menü auf 80x24"),
        (100, 32, [], "Menü auf 100x32"),
        (100, 32, ["down", "down"], "Zwei Punkte weiter"),
        (100, 32, ["3"], "Punkt 3 per Ziffer: Kunden"),
        (100, 32, ["6"], "Punkt 6: Stammdaten"),
        (100, 32, ["4"], "Punkt 4: Leistungen"),
    ]

    for breite, hoehe, befehle, kopf in faelle:
        print(f"=== {kopf} ===")
        print(await zeige(breite, hoehe, befehle))
        print()


if __name__ == "__main__":
    asyncio.run(main())
