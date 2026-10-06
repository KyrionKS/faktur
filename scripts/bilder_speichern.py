#!/usr/bin/env python3
"""Rendert Bildschirme der App als PNG.

Aus dem Bildschirmspeicher kommen die Textabschnitte mit ihren echten Farben.
Mit Pillow wird daraus ein PNG, so wie es im Terminal aussieht. Damit lässt
sich der Kontrast ansehen statt nur nachrechnen.

    .venv/bin/python scripts/bilder_speichern.py
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from faktur.app import FakturApp  # noqa: E402

#: Wohin die Bilder kommen.
ZIEL = Path(__file__).resolve().parents[1] / "beispiele"

#: Die Schrift. Eine Monospace, damit die Spalten stehen.
SCHRIFT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

#: Die Grössen der Zeichen in Pixeln.
GROSSE = 17
ZEILE = 22
RAND = 16

#: Die Breite einer Zeichenzelle.
ZELLE = 10


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
    """Entscheidet, ob ein Grund hell ist.

    Args:
        rgb: Der Grund.

    Returns:
        ``True``, wenn der Grund hell ist.
    """
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2] > 128


def zeichnen(app: FakturApp, ziel: Path) -> Path:
    """Schreibt den aktuellen Bildschirm als PNG.

    Args:
        app: Die laufende App.
        ziel: Die Zieldatei.

    Returns:
        Der Pfad des geschriebenen Bildes.
    """
    streifen = app.screen._compositor.render_strips()
    # Die Länge eines Streifens ist die Zahl der Abschnitte, nicht die der
    # Spalten. Für die Breite zählt, was tatsächlich Text ist.
    breite = max(
        (sum(len(teil.text) for teil in s) for s in streifen),
        default=80,
    )
    hoehe = max(len(streifen), 1)

    grund = _farbe(app.screen.styles.background, (30, 30, 30))
    schrift = ImageFont.truetype(SCHRIFT, GROSSE)

    bild = Image.new(
        "RGB",
        (breite * ZELLE + RAND * 2, hoehe * ZEILE + RAND * 2),
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
            farbe = _farbe(getattr(stil, "color", None), grund)
            if farbe == grund and not _ist_hell(grund):
                farbe = (210, 210, 210)
            stift.text(
                (RAND + spalte * ZELLE, RAND + nummer * ZEILE),
                text,
                font=schrift,
                fill=farbe,
            )
            spalte += len(text)

    ziel.parent.mkdir(parents=True, exist_ok=True)
    bild.save(ziel)
    return ziel


async def aufnehmen(befehle: list[str], name: str) -> Path:
    """Startet die App, drückt Tasten und schreibt ein Bild.

    Args:
        befehle: Die Tasten in Reihenfolge.
        name: Der Name der Datei ohne Endung.

    Returns:
        Der Pfad des Bildes.
    """
    with tempfile.TemporaryDirectory() as ordner:
        app = FakturApp(Path(ordner) / "bild.db")
        async with app.run_test(size=(100, 34)) as pilot:
            await pilot.pause()
            for taste in befehle:
                await pilot.press(taste)
                await pilot.pause()
            return zeichnen(app, ZIEL / f"{name}.png")


#: Welche Bildschirme aufgenommen werden: Name und die Tasten dorthin.
FAELLE = (
    ("01_menue", []),
    ("02_stammdaten", ["6"]),
    ("03_brieftext", ["6", "3"]),
    ("04_kunden", ["3"]),
    ("05_leistungen", ["4"]),
)


async def main() -> None:
    """Schreibt alle Bilder.

    Returns:
        Nichts. Schreibt nach stdout.
    """
    for name, befehle in FAELLE:
        pfad = await aufnehmen(befehle, name)
        print(f"  {pfad.name:<22} {pfad.stat().st_size:>7} Bytes")


if __name__ == "__main__":
    asyncio.run(main())
