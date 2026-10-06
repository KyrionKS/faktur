#!/usr/bin/env python3
"""Legt Beispieldaten an und prüft den ganzen Weg.

Der Durchlauf beantwortet keine Fragen, legt Stammdaten, Logo, Kunde,
Angebot und Rechnung an und schreibt die PDF nach ``beispiele/``. Damit
lässt sich ohne Menü prüfen, ob der Weg noch trägt.
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from faktur import betraege, dateien, db, einstellungen, pdf  # noqa: E402
from faktur.screens.dokumente import dateiname  # noqa: E402

#: Wohin die Beispieldateien geschrieben werden.
ZIEL = Path(__file__).resolve().parents[1] / "beispiele"

#: Die Datenbank für den Durchlauf. Liegt in /tmp, damit die echten Daten
#: unangetastet bleiben.
TESTDATENBANK = Path("/tmp/faktur_durchlauf.db")

#: Die Stammdaten der New Air Media Group.
STAMMDATEN = {
    "firma": "New Air Media Group",
    "zusatz": "Tonstudio & Medienproduktion",
    "strasse": "Soundweg 12",
    "plz": "10999",
    "ort": "Berlin",
    "telefon": "+49 30 1234567",
    "email": "ton@newair.media",
    "webseite": "newair.media",
    "inhaber": "Kyrion",
    "bank": "Deutsche Kreditbank",
    "iban": "DE02 1203 0000 0000 2020 51",
    "bic": "BYLADEM1001",
    "steuernummer": "12/345/67890",
}

#: Der Kunde für das Beispiel.
KUNDE = {
    "firma": "Soundcheck GmbH",
    "ansprechpartner": "Herr Max Mustermann",
    "strasse": "Klangstrasse 3",
    "plz": "10115",
    "ort": "Berlin",
    "email": "m.mustermann@soundcheck.de",
    "telefon": "+49 30 9988776",
}

#: Die Positionen von Angebot und Rechnung.
ANGEBOT_POSITIONEN = (
    ("Aufnahme Ton", "2", "Tag", "850"),
    ("Mischung und Mastering", "12", "Stunde", "95"),
)

RECHNUNG_POSITIONEN = (("Jingle / Sounddesign", "1", "Stück", "450"),)


def _positionen(
    verbindung: sqlite3.Connection, angaben: tuple[tuple[str, str, str, str], ...]
) -> list[dict[str, str | float | int | None]]:
    """Baut die Positionsliste aus der Preisliste.

    Args:
        verbindung: Die Datenbankverbindung.
        angaben: Die Positionen als Bezeichnung, Menge, Einheit, Preis.

    Returns:
        Die Liste für :func:`faktur.dateien.dokument_speichern`.
    """
    preise = {
        leistung["bezeichnung"]: leistung["id"]
        for leistung in dateien.leistungen(verbindung)
    }
    return [
        {
            "leistung_id": preise.get(bezeichnung),
            "bezeichnung": bezeichnung,
            "menge": menge,
            "einheit": einheit,
            "preis": preis,
        }
        for bezeichnung, menge, einheit, preis in angaben
    ]


def stammdaten_setzen(verbindung: sqlite3.Connection) -> None:
    """Trägt die Stammdaten ein.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    for name, wert in STAMMDATEN.items():
        einstellungen.speichere(verbindung, name, wert)


def logo_uebernehmen(verbindung: sqlite3.Connection) -> None:
    """Sucht ein Logo und merkt sich den Pfad.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    for kandidat in (
        Path.home() / "Vibecoding" / "logo.png",
        Path(__file__).resolve().parents[2] / "logo.png",
    ):
        if kandidat.is_file():
            einstellungen.logo_uebernehmen(verbindung, kandidat)
            print(f"  Logo       {kandidat}")
            return
    print("  Logo       keines gefunden, die PDF entsteht ohne.")


def dokument_bauen(
    verbindung: sqlite3.Connection,
    art: str,
    nummer: str,
    kunde_id: int,
    zusatz: dict[str, str],
    positionen: tuple[tuple[str, str, str, str], ...],
) -> None:
    """Legt ein Dokument an und schreibt die PDF.

    Args:
        verbindung: Die Datenbankverbindung.
        art: ``angebot`` oder ``rechnung``.
        nummer: Die Nummer des Dokuments.
        kunde_id: Die Nummer des Kunden.
        zusatz: Weitere Kopfangaben wie ``faellig``.
        positionen: Die Positionen.
    """
    dokument_id = dateien.dokument_speichern(
        verbindung,
        {
            "art": art,
            "nummer": nummer,
            "kunde_id": kunde_id,
            "datum": "06.10.2026",
            **zusatz,
        },
        _positionen(verbindung, positionen),
    )

    dokument = dateien.dokument_holen(verbindung, dokument_id)
    if dokument is None:
        raise RuntimeError(f"Das Dokument {nummer} liess sich nicht lesen.")

    ZIEL.mkdir(parents=True, exist_ok=True)
    ziel = ZIEL / f"{dateiname(dokument, art)}.pdf"
    pdf.erzeugen(verbindung, dokument, ziel)

    summe = dateien.summe_von(verbindung, dokument_id)
    beschriftung = "Angebot" if art == "angebot" else "Rechnung"
    print(f"  {beschriftung:<9} {nummer:<16} {betraege.euro(summe):>13}   {ziel.name}")


def main() -> int:
    """Führt den ganzen Weg einmal durch.

    Returns:
        ``0``, wenn beide Dokumente geschrieben wurden.
    """
    TESTDATENBANK.unlink(missing_ok=True)
    shutil.rmtree(ZIEL, ignore_errors=True)

    verbindung = db.verbinden(TESTDATENBANK)

    print("Durchlauf")
    stammdaten_setzen(verbindung)
    logo_uebernehmen(verbindung)

    kunde_id = dateien.kunde_speichern(verbindung, KUNDE)
    print(f"  Kunde      {KUNDE['firma']} (Nummer {kunde_id})")
    print(f"  Logo       {einstellungen.logo_pfad(verbindung) or 'keins'}")
    print()

    dokument_bauen(
        verbindung,
        "angebot",
        dateien.naechste_nummer(verbindung),
        kunde_id,
        {"gueltig_bis": betraege.plus_tage(21)},
        ANGEBOT_POSITIONEN,
    )
    dokument_bauen(
        verbindung,
        "rechnung",
        dateien.naechste_nummer(verbindung),
        kunde_id,
        {"faellig": betraege.plus_tage(14)},
        RECHNUNG_POSITIONEN,
    )

    anzahl = len(dateien.dokumente(verbindung))
    verbindung.close()

    print()
    print(f"{anzahl} Dokumente in der Datenbank, die PDF liegen in {ZIEL}")

    return 0 if anzahl == 2 else 1


if __name__ == "__main__":
    raise SystemExit(main())
