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
from textual.keys import KEY_TO_UNICODE_NAME, Keys

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

#: Die Namen, die Textual als **eine** Taste versteht.
#:
#: ``escape``, ``enter``, ``home`` und so weiter.
TASTENNAMEN = {name.value for name in Keys} | set(KEY_TO_UNICODE_NAME)


def tasten(screen: object, befehl: str) -> list[str]:
    """Zerlegt einen Eintrag der Fallliste in echte Tastendrücke.

    Textual erwartet einzelne Tasten. Ein Wort wie ``"check"`` wird als
    Tastenname nachgeschlagen, nicht gefunden — und es passiert einfach
    nichts, ohne jede Fehlermeldung. Die Fallliste bleibt trotzdem lesbar,
    weil hier entschieden wird.

    Die Frage wird **dem offenen Bildschirm** gestellt, nicht einer Liste
    im Skript: ``suche`` ist eine Taste des Programms, ``check`` ist es
    nicht, und beides sind fünf Buchstaben. Nur der Bildschirm weiß, was
    eine Taste ist — die Tastenbelegung wechselt mit jeder Seite.

    Args:
        screen: Der gerade offene Bildschirm.
        befehl: Ein Eintrag aus der Fallliste.

    Returns:
        Die Tasten in der Reihenfolge, in der sie zu drücken sind.
    """
    if befehl in TASTENNAMEN:
        return [befehl]

    belegung = screen._merged_bindings.key_to_bindings
    if befehl in belegung:
        return [befehl]

    return list(befehl)


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


async def aufnehmen(
    befehle: list[str],
    name: str,
    vorbereiten: object = None,
    erwartet: str = "",
) -> Path:
    """Startet die App, drückt Tasten und schreibt ein Bild.

    Args:
        befehle: Die Tasten in Reihenfolge.
        name: Der Name der Datei ohne Endung.
        vorbereiten: Eine Funktion, die vor dem ersten Tastendruck läuft.
        erwartet: Der Name des Bildschirms, der danach offen sein muss.

    Returns:
        Der Pfad des Bildes.

    Raises:
        AssertionError: Wenn ein anderer Bildschirm offen ist als der, für
            den das Bild benannt ist.
    """
    with tempfile.TemporaryDirectory() as ordner:
        app = FakturApp(Path(ordner) / "bild.db")
        async with app.run_test(size=(100, 34)) as pilot:
            await pilot.pause()
            if vorbereiten is not None:
                await vorbereiten(app, pilot)  # type: ignore[operator]
                await pilot.pause()
            for befehl in befehle:
                for einzelne in tasten(app.screen, befehl):
                    await pilot.press(einzelne)
                    await pilot.pause()

            if erwartet:
                offen = type(app.screen).__name__
                assert offen == erwartet, (
                    f"{name}: Nach den Tasten {befehle} ist {offen} offen, "
                    f"erwartet wurde {erwartet}. Die Nummer im Menü hat sich "
                    "verschoben, und das Bild würde unter dem falschen "
                    "Namen gespeichert."
                )

            return zeichnen(app, ZIEL / f"{name}.png")


async def _mit_angebot(app: FakturApp, pilot: object) -> None:
    """Legt einen Kunden und ein Angebot an, damit es etwas zu sehen gibt.

    Args:
        app: Die laufende App.
        pilot: Die Teststeuerung von Textual.
    """
    from faktur import dateien

    kunde_id = dateien.kunde_speichern(app.db, {"firma": "Soundcheck GmbH"})
    leistung = dateien.leistungen(app.db)[0]
    dateien.dokument_speichern(
        app.db,
        {
            "art": "angebot",
            "nummer": "0001",
            "kunde_id": kunde_id,
            "datum": "06.10.2026",
        },
        [
            {
                "leistung_id": leistung["id"],
                "bezeichnung": leistung["bezeichnung"],
                "menge": "2",
                "einheit": leistung["einheit"],
                "preis": "850",
            }
        ],
    )


async def _mit_rechnung(app: FakturApp, pilot: object) -> None:
    """Legt zwei offene Rechnungen an.

    Zwei, damit die Liste etwas zu zeigen hat und nicht nur einen leeren
    Rahmen. Für den Bildschirm *Offene Forderungen* nötig: Dort steht ein
    Angebot nie, weil es nicht in Rechnung gestellt wird.

    Args:
        app: Die laufende App.
        pilot: Die Teststeuerung von Textual.
    """
    from faktur import betraege, dateien

    kunde_id = dateien.kunde_speichern(app.db, {"firma": "Soundcheck GmbH"})
    leistung = dateien.leistungen(app.db)[0]

    for nummer, (menge, faellig) in enumerate(
        (("2", betraege.plus_tage(-20)), ("1", betraege.plus_tage(20))), start=1
    ):
        dateien.dokument_speichern(
            app.db,
            {
                "art": "rechnung",
                "nummer": f"000{nummer}",
                "kunde_id": kunde_id,
                "datum": "06.10.2026",
                "faellig": faellig,
            },
            [
                {
                    "leistung_id": leistung["id"],
                    "bezeichnung": leistung["bezeichnung"],
                    "menge": menge,
                    "einheit": leistung["einheit"],
                    "preis": "850",
                }
            ],
        )


async def _mit_kunden(app: FakturApp, pilot: object) -> None:
    """Legt mehrere Kunden an, damit die Suche etwas zu zeigen hat.

    Bei drei Kunden sieht man nichts. Bei sieben schon.

    Args:
        app: Die laufende App.
        pilot: Die Teststeuerung von Textual.
    """
    from faktur import dateien

    for nummer, firma in enumerate(
        (
            "Soundcheck GmbH",
            "NeunUndNeun Film",
            "Tonstudio Hamburg",
            "CHECK Gesellschaft",
            "Buchhandlung am Markt",
            "Radio Nordfunk",
            "Kamerawerkstatt Süd",
        ),
        start=1,
    ):
        dateien.kunde_speichern(
            app.db,
            {
                "firma": firma,
                "ansprechpartner": f"Ansprechpartner {nummer}",
                "ort": f"Ort {nummer}",
            },
        )


async def _mit_positionen(app: FakturApp, pilot: object) -> None:
    """Legt einen Kunden und ein Angebot mit Rabatt an.

    Args:
        app: Die laufende App.
        pilot: Die Teststeuerung von Textual.
    """
    from faktur import dateien

    kunde_id = dateien.kunde_speichern(app.db, {"firma": "Soundcheck GmbH"})
    leistung = dateien.leistungen(app.db)[0]
    dateien.dokument_speichern(
        app.db,
        {
            "art": "angebot",
            "nummer": "0001",
            "kunde_id": kunde_id,
            "datum": "06.10.2026",
        },
        [
            {
                "leistung_id": leistung["id"],
                "bezeichnung": leistung["bezeichnung"],
                "menge": "2",
                "einheit": leistung["einheit"],
                "preis": "850",
            },
            {"bezeichnung": "Rabatt", "menge": "1", "einheit": "", "preis": "-300"},
        ],
    )


#: Welche Bildschirme aufgenommen werden: Name, Tasten, Vorbereitung,
#: und der Bildschirm, der danach offen sein muss.
#:
#: Das vierte Feld ist nicht hübsch, sondern nötig. Beim Umnummerieren des
#: Hauptmenüs in 0.6 blieben hier die alten Zahlen stehen, und fortan
#: speicherte das Skript Bildschirme unter fremden Namen: Das Bild
#: ``06_dokumente`` zeigte die offenen Forderungen, und niemand hat es
#: gemerkt, weil ein Bild mit Suchleiste und Liste nach wie vor plausibel
#: aussah.
#:
#: Deshalb steht der Bildschirm, der erwartet wird, direkt daneben, und
#: :func:`aufnehmen` prüft ihn. Falsche Nummer, falsches Bild, deutliche
#: Meldung.
FAELLE = (
    ("01_menue", [], None, "MenueScreen"),
    ("02_stammdaten", ["7"], None, "StammdatenScreen"),
    ("03_brieftext", ["7", "3"], None, "BausteinScreen"),
    ("04_kunden", ["3"], _mit_angebot, "KundenListeScreen"),
    ("05_leistungen", ["4"], None, "LeistungenScreen"),
    ("06_dokumente", ["6"], _mit_angebot, "DokumentenScreen"),
    ("07_umwandlung", ["6", "r"], _mit_angebot, "KontrolleScreen"),
    ("08_positionen", ["1", "enter"], _mit_positionen, "PositionenScreen"),
    ("09_aussehen", ["7", "6"], None, "AussehenScreen"),
    ("10_aussehen_rechnung", ["7", "6", "home", "right"], None, "AussehenScreen"),
    ("11_offene", ["5"], _mit_rechnung, "OffeneScreen"),
    ("12_kundensuche", ["1", "suche", "check"], _mit_kunden, "EditorScreen"),
    # "p" fuer "Position aus der Preisliste" ("+" laesst sich nicht senden).
    (
        "13_leistungssuche",
        ["1", "1", "p", "suche", "m"],
        _mit_kunden,
        "LeistungAuswahlScreen",
    ),
)


async def main() -> None:
    """Schreibt alle Bilder.

    Returns:
        Nichts. Schreibt nach stdout.
    """
    for name, befehle, vorbereiten, erwartet in FAELLE:
        pfad = await aufnehmen(befehle, name, vorbereiten, erwartet)
        print(f"  {pfad.name:<22} {pfad.stat().st_size:>7} Bytes")


if __name__ == "__main__":
    asyncio.run(main())
