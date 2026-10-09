"""Was man sieht, ist was man bekommt.

Auf der Kundenliste stimmte bis 0.8.2 die Anzeige und die Liste hinter ihr
nicht überein: Gefiltert wurden nur die Zeilen der Tabelle, die Kundenliste
selbst blieb ganz. Wer *Zeta Tonwerk* suchte, sah *Zeta Tonwerk*, drückte
Enter und bekam *Alpha Klangstudio* — und mit Entf fragte das Programm
danach, ob *Alpha Klangstudio* samt Dokumenten gelöscht werden soll.

Niemand hat es bemerkt, weil kein Test diese Liste je durchsucht hat. Der
Durchlauf `ablauf_pruefen.py` sucht im *Editor*, nicht auf der Kundenliste,
und `test_auswahl_suche.py` sah sich den Kundenschritt im Editor an.

Dieser Wächter macht genau das, was vorher niemand gemacht hat: Er legt
mehrere Kunden an, filtert auf einen, und prüft für jede Aktion der Liste —
öffnen, ändern, löschen — ob der **gesehene** Kunde gemeint ist.
"""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest
from faktur import dateien
from faktur.app import FakturApp

#: Die Kunden, in dieser Reihenfolge. Der gesuchte steht **nicht** an erster
#: Stelle, damit ein Fehler sofort auffaellt.
KUNDEN = ("Alpha Klangstudio", "Beta Tonwerk", "Gamma Tonbau", "Delta Film")

#: Wonach gesucht wird. Passt auf genau einen, und zwar auf den zweiten.
SUCHBEGRIFF = "Beta"


def _lege_kunden_an(db: sqlite3.Connection) -> None:
    """Legt die Kunden an.

    Args:
        db: Die Datenbankverbindung.
    """
    for firma in KUNDEN:
        dateien.kunde_speichern(db, {"firma": firma})


def _bild(app: FakturApp) -> list[str]:
    """Liest den Bildschirm als Zeilen.

    Args:
        app: Die laufende App.

    Returns:
        Die Zeilen ohne Leerzeichen am Ende.
    """
    roh = "\n".join(teil.text for teil in app.screen._compositor.render_strips())
    return [zeile.strip() for zeile in roh.splitlines() if zeile.strip()]


def _suche_und_druecke(ordner: Path, befehle: list[str]) -> tuple[str, list[str]]:
    """Sucht einen Kunden und drückt danach Tasten.

    Args:
        ordner: Der Prüfordner.
        befehle: Die Tasten nach der Suche, etwa ``["enter"]``.

    Returns:
        Der Name des Bildschirms und sein Bild als Zeilen.
    """

    async def lauf() -> tuple[str, list[str]]:
        app = FakturApp(ordner / "suche.db")
        async with app.run_test(size=(90, 30)) as pilot:
            await pilot.pause()
            _lege_kunden_an(app.db)

            await pilot.press("3")  # Kunden
            await pilot.pause()
            await pilot.press("suche")
            await pilot.pause()
            for zeichen in SUCHBEGRIFF:
                await pilot.press(zeichen)
                await pilot.pause()
            await pilot.press("tab")  # aus dem Suchfeld in die Liste
            await pilot.pause()

            for taste in befehle:
                await pilot.press(taste)
                await pilot.pause()

            return type(app.screen).__name__, _bild(app)

    return asyncio.run(lauf())


@pytest.mark.parametrize(
    ("taste", "erwartet"),
    [("enter", "KundeDetailScreen"), ("delete", "FrageScreen")],
    ids=["oeffnen", "loeschen-frage"],
)
def test_die_aktion_gilt_dem_gesehenen_kunden(
    tmp_path: Path, taste: str, erwartet: str
) -> None:
    """Nach dem Filtern muss jede Aktion den Kunden treffen, den man sieht.

    Args:
        tmp_path: Der Prüfordner.
        taste: Die Taste nach der Suche.
        erwartet: Der Bildschirm, der danach offen sein muss.

    Raises:
        AssertionError: Wenn ein anderer Kunde gemeint ist als der gefundene.
    """
    bildschirm, bild = _suche_und_druecke(tmp_path, [taste])

    assert bildschirm == erwartet, (
        f"Nach der Suche und {taste!r} ist {bildschirm} offen, "
        f"erwartet wurde {erwartet}."
    )

    fremde = [zeile for zeile in bild if any(f in zeile for f in KUNDEN)]
    assert fremde, "Der Kundenname steht nirgends im Bild — der Test prueft nichts."

    assert all(SUCHBEGRIFF.lower() in zeile.lower() for zeile in fremde), (
        f"Die Liste zeigt {SUCHBEGRIFF!r}, gemeint war aber:\n  "
        + "\n  ".join(fremde)
        + "\nDas ist der Fehler von 0.8.1: Anzeige und Liste hinter ihr "
        "gehen auseinander."
    )


def test_und_die_liste_davor_bleibt_vollstaendig(tmp_path: Path) -> None:
    """Nach dem Filtern muss die ungefilterte Liste noch da sein.

    Sonst ist die Liste eine Einbahnstraße: Was ein Backspace aus einem
    Suchbegriff entfernt, kommt nicht zurück.

    Args:
        tmp_path: Der Prüfordner.

    Raises:
        AssertionError: Wenn die Liste nach dem Zurücktippen zu kurz bleibt.
    """
    anzahl = {}

    async def lauf() -> int:
        app = FakturApp(tmp_path / "vollstaendig.db")
        async with app.run_test(size=(90, 30)) as pilot:
            await pilot.pause()
            _lege_kunden_an(app.db)

            await pilot.press("3")
            await pilot.pause()
            await pilot.press("suche")
            await pilot.pause()
            for zeichen in SUCHBEGRIFF:
                await pilot.press(zeichen)
                await pilot.pause()

            anzahl["gefiltert"] = len(app.screen.query_one("Tabelle").zeilen)

            for _ in SUCHBEGRIFF:
                await pilot.press("backspace")
                await pilot.pause()

            anzahl["zurueck"] = len(app.screen.query_one("Tabelle").zeilen)
            return len(app.screen.alle_kunden)

    gesamt = asyncio.run(lauf())

    assert anzahl["gefiltert"] == 1, (
        f"'{SUCHBEGRIFF}' passt auf genau einen Kunden, gefunden wurden "
        f"{anzahl['gefiltert']}."
    )
    assert anzahl["zurueck"] == gesamt == len(KUNDEN), (
        f"Nach dem Zurücktippen stehen {anzahl['zurueck']} Kunden da, "
        f"es gibt aber {len(KUNDEN)}. Die Liste ist eine Einbahnstraße."
    )
