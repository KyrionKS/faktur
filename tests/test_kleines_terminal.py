"""Darf man alles sehen, was man ausfüllen muss?

Bis 0.8.1 hat das Programm die unteren Felder eines Formulars abgeschnitten
und sich nicht rollen lassen. Wer ein Kundenformular in einem Fenster von 34
Zeilen ausfüllte, sah drei von acht Feldern — und die anderen fünf waren
trotzdem da, sie waren nur nicht zu sehen.

Der Fehler war nicht sichtbar, weil das Formular **in** die Höhe hineingedrückt
wurde, statt darüber hinauszuragen.

Dieser Wächter geht jeden Bildschirm bei kleiner Fensterhöhe durch, tabbt durch
alle Eingabefelder und prüft nach jedem Tastendruck, ob das Feld, auf dem der
Cursor steht, auch wirklich im Bild ist.

## Warum nicht nachrechnen, sondern nachmachen

Der erste Versuch hat die Widget-Bäume vermessen und gefragt: Reicht ein Kind
über den Bereich seines Elternteils hinaus? Das klingt richtig und war falsch.

Im alten Zustand meldete das Formular ``max_scroll_y = 14`` — es **konnte**
also rollen. Nur tat es nie: ``scroll_y`` blieb auf 0, weil kein Ereignis kam,
das scrollen ließ. Ein Vermessen sagt „erreichbar", der Nutzer sieht trotzdem
nichts.

Deshalb wird hier nicht gerechnet, sondern getan: dasselbe wie im Betrieb, ein
`tab` nach dem anderen, und nach jedem Schritt nachsehen, was zu sehen ist. Was
der Nutzer nicht erreicht, wird auch hier nicht erreicht.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from faktur import dateien
from faktur.app import FakturApp
from textual.widgets import Input, TextArea

#: Das Fenster, auf dem alles geprüft wird. Klein genug, dass es auffällt.
BREITE = 90
HOEHE = 20

#: Der Weg zu jedem Bildschirm mit einem Formular.
WEGE = [
    ("Kundenformular", ["3", "n"]),
    ("Stammdaten-Formular", ["7", "enter"]),
    ("Leistungsformular", ["4", "n"]),
    ("Brieftext Angebote", ["7", "3"]),
    ("Brieftext Rechnungen", ["7", "4"]),
]


def _durchtabben(ordner: Path, tasten: list[str]) -> list[str]:
    """Tabbt durch den Bildschirm und meldet jedes Feld, das nicht zu sehen ist.

    Args:
        ordner: Der Prüfordner für die Datenbank.
        tasten: Der Weg zum Bildschirm.

    Returns:
        Eine Beschreibung je Feld, das nicht sichtbar war. Leer ist gut.
    """

    async def lauf() -> list[str]:
        app = FakturApp(ordner / "klein.db")
        async with app.run_test(size=(BREITE, HOEHE)) as pilot:
            await pilot.pause()
            dateien.kunde_speichern(app.db, {"firma": "Soundcheck GmbH"})

            for taste in tasten:
                await pilot.press(taste)
                await pilot.pause()
            await pilot.pause()

            fenster = app.screen.region
            felder = list(app.screen.query(Input)) + list(app.screen.query(TextArea))
            if not felder:
                return []

            gefunden: list[str] = []
            for schritt in range(len(felder)):
                await pilot.press("tab")
                await pilot.pause()

                feld = app.focused
                if feld is None:
                    continue

                oben_ok = feld.region.y >= fenster.y
                unten_ok = feld.region.bottom <= fenster.bottom
                if not (oben_ok and unten_ok):
                    gefunden.append(
                        f"{schritt + 1}. Feld ({type(feld).__name__}) "
                        f"liegt bei {feld.region.y}-{feld.region.bottom}, "
                        f"das Fenster zeigt {fenster.y}-{fenster.bottom}"
                    )

            return gefunden

    return asyncio.run(lauf())


@pytest.mark.parametrize(("name", "tasten"), WEGE, ids=[w[0] for w in WEGE])
def test_jedes_feld_ist_zu_erreichen(
    tmp_path: Path, name: str, tasten: list[str]
) -> None:
    """Bei kleinem Fenster muss jedes Feld sichtbar werden, wenn man dorthin tabbt.

    Args:
        tmp_path: Der Prüfordner.
        name: Der Bildschirm in lesbarer Form.
        tasten: Der Weg zum Bildschirm.

    Raises:
        AssertionError: Wenn ein Feld im Bild fehlt, obwohl der Cursor dort steht.
    """
    gefunden = _durchtabben(tmp_path, tasten)

    assert gefunden == [], (
        f"{name}: Bei einem Fenster von {BREITE}x{HOEHE} war nach dem Tabben "
        "ein Feld nicht zu sehen:\n  " + "\n  ".join(gefunden) + "\nWer hier "
        "ein Formular ausfüllt, übersieht Felder. Meist fehlt einem "
        "Container das `height: auto`, dann schrumpft er in die Höhe hinein, "
        "statt darüber hinauszuragen."
    )


def test_der_waechter_findet_auch_den_alten_fehler(tmp_path: Path) -> None:
    """Der Wächter muss anschlagen, wenn der alte Fehler wieder da ist.

    Sonst wäre er eine Prüfung, die nichts prüft. Deshalb wird der Fehler
    hier absichtlich wiederhergestellt: Das Formular bekommt eine feste
    Höhe, schrumpft also wieder in den Platz hinein statt darüber
    hinauszuragen — genau das war bis 0.8.1 der Zustand.

    Args:
        tmp_path: Der Prüfordner.

    Raises:
        AssertionError: Wenn die Regel den wiederhergestellten Fehler
            übersieht.
    """

    async def lauf() -> list[str]:
        app = FakturApp(tmp_path / "kaputt.db")
        async with app.run_test(size=(BREITE, HOEHE)) as pilot:
            await pilot.pause()
            # Der Fehler von 0.8: eine feste Hoehe statt ``height: auto``.
            app.stylesheet.add_source(
                ".formular { height: 10 !important; }", read_from=None
            )
            app.refresh_css()
            await pilot.pause()

            dateien.kunde_speichern(app.db, {"firma": "Soundcheck GmbH"})
            for taste in ["3", "n"]:
                await pilot.press(taste)
                await pilot.pause()
            await pilot.pause()

            fenster = app.screen.region
            gefunden = []
            for schritt in range(len(list(app.screen.query(Input)))):
                await pilot.press("tab")
                await pilot.pause()
                feld = app.focused
                if feld is None:
                    continue
                if feld.region.bottom > fenster.bottom:
                    gefunden.append(
                        f"{schritt + 1}. Feld reicht bis {feld.region.bottom}"
                    )
            return gefunden

    gefunden = asyncio.run(lauf())

    assert gefunden, (
        "Der Wächter meldet nichts, obwohl das Formular gerade wieder "
        "abgeschnitten wurde. Er prüft also nichts."
    )
