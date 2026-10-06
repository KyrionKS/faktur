#!/usr/bin/env python3
"""Rendert die Oberfläche als Bild.

Aus dem Bildschirmspeicher kommen die Textabschnitte mit ihren echten Farben.
Mit Pillow wird daraus ein PNG, so wie es im Terminal aussieht. Damit lässt
sich der Kontrast ansehen statt nur nachrechnen.

    .venv/bin/python scripts/bild_als_png.py
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from faktur.app import FakturApp  # noqa: E402

#: Wohin das Bild kommt.
ZIEL = Path(__file__).resolve().parents[1] / "beispiele" / "menue.png"

#: Die Schrift. Eine Monospace, damit die Spalten stehen.
SCHRIFT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

#: Die Grössen der Zeichen in Pixeln.
GROSSE = 17
ZEILE = 22
RAND = 16


def _farbe(angabe: object, standard: tuple[int, int, int]) -> tuple[int, int, int]:
    """Macht aus einer Farbangabe ein RGB-Tupel.

    Args:
        angabe: Die Farbe aus Rich, ein ``Color`` oder ``None``.
        standard: Was gilt, wenn keine Farbe dasteht.

    Returns:
        Das Tripel für Pillow.
    """
    if angabe is None:
        return standard
    text = str(angabe)
    if text.startswith("#") and len(text) == 7:
        text = text[1:]
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    return standard


def _ist_hell(rgb: tuple[int, int, int]) -> bool:
    """Entscheidet, ob eine Schrift hell auf einem Grund sein muss.

    Args:
        rgb: Der Hintergrund.

    Returns:
        ``True``, wenn der Hintergrund hell ist.
    """
    helligkeit = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    return helligkeit > 128


def zeichnen(app: FakturApp, ziel: Path) -> Path:
    """Schreibt den aktuellen Bildschirm als PNG.

    Args:
        app: Die laufende App.
        ziel: Die Zieldatei.

    Returns:
        Der Pfad des geschriebenen Bildes.
    """
    streifen = app.screen._compositor.render_strips()
    breite = max((len(streifen[0]) if streifen else 0), 80)
    hoehe = len(streifen) or 24

    grund = _farbe(app.screen.styles.background, (30, 30, 30))
    schrift = ImageFont.truetype(SCHRIFT, GROSSE)
    fett = ImageFont.truetype(SCHRIFT, GROSSE)

    zellen_x = GROSSE * 0 + 10
    bild = Image.new(
        "RGB",
        (breite * zellen_x + RAND * 2, hoehe * ZEILE + RAND * 2),
        grund,
    )
    stift = ImageDraw.Draw(bild)

    for nummer, streifen_ in enumerate(streifen):
        spalte = 0
        for abschnitt in streifen_:
            text = abschnitt.text
            if not text:
                continue
            stil = getattr(abschnitt, "style", None)
            vordergrund = _farbe(getattr(stil, "color", None), grund)
            if not _ist_hell(grund):
                vordergrund = vordergrund if vordergrund != grund else (200, 200, 200)
            stift.text(
                (RAND + spalte * zellen_x, RAND + nummer * ZEILE),
                text,
                font=fett if getattr(stil, "bold", False) else schrift,
                fill=vordergrund,
            )
            spalte += len(text)

    ziel.parent.mkdir(parents=True, exist_ok=True)
    bild.save(ziel)
    return ziel


async def aufnehmen() -> Path:
    """Startet die App und schreibt ein Bild von der Startseite.

    Returns:
        Der Pfad des Bildes.
    """
    with tempfile.TemporaryDirectory() as ordner:
        app = FakturApp(Path(ordner) / "bild.db")
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            return zeichnen(app, ZIEL)


def main() -> int:
    """Rendert das Bild und sagt, wo es liegt.

    Returns:
        ``0``, wenn die Datei da ist.
    """
    pfad = asyncio.run(aufnehmen())
    print(f"Gespeichert: {pfad}  ({pfad.stat().st_size} Bytes)")
    return 0 if pfad.is_file() else 1


if __name__ == "__main__":
    raise SystemExit(main())
