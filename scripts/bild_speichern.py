#!/usr/bin/env python3
"""Legt eine Seite der Oberfläche als Bild ab.

Textual kann das, was es zeichnet, als SVG ausgeben. Damit lässt sich ansehen,
wie die Oberfläche wirklich aussieht, mit den echten Farben — und nicht nur
als Text mit lauter Leerzeichen.

    .venv/bin/python scripts/bild_speichern.py
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from faktur.app import FakturApp  # noqa: E402

#: Wohin das Bild kommt.
ZIEL = Path(__file__).resolve().parents[1] / "beispiele" / "menue.svg"


async def speichern() -> Path:
    """Startet die App, drückt keine Taste und schreibt das Bild.

    Returns:
        Der Pfad der Datei.
    """
    with tempfile.TemporaryDirectory() as ordner:
        app = FakturApp(Path(ordner) / "bild.db")
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            ZIEL.parent.mkdir(parents=True, exist_ok=True)
            app.save_screenshot(str(ZIEL))
            await pilot.pause()
    return ZIEL


def main() -> int:
    """Schreibt den Screenshot und sagt, wo er liegt.

    Returns:
        ``0``, wenn die Datei da ist.
    """
    pfad = asyncio.run(speichern())
    print(f"Gespeichert: {pfad}  ({pfad.stat().st_size} Bytes)")
    return 0 if pfad.is_file() else 1


if __name__ == "__main__":
    raise SystemExit(main())
