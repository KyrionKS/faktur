"""Schema und Verbindung zur Datenbank.

Die Daten liegen in einer SQLite-Datei im Heimverzeichnis. Es gibt keinen
Server und keine Konfigurationsdatei: ``~/.faktur/faktur.db`` ist die ganze
Datenhaltung.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

#: Der Ordner, in dem die Datenbank und das Logo liegen.
DATENORDNER = Path.home() / ".faktur"

#: Die Datenbank selbst.
DATENBANK = DATENORDNER / "faktur.db"

#: Das Logo fuer die PDF, falls in den Einstellungen keines liegt.
STANDARD_LOGO = DATENORDNER / "logo.png"

#: Wo die erzeugten PDF landen.
RECHNUNGEN = Path.home() / "Rechnungen"

#: Das Schema. Wird bei jedem Start angelegt, wenn etwas fehlt.
SCHEMA = """
CREATE TABLE IF NOT EXISTS einstellungen (
    schluessel TEXT PRIMARY KEY,
    wert       TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS kunden (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    firma            TEXT NOT NULL,
    ansprechpartner  TEXT NOT NULL DEFAULT '',
    strasse          TEXT NOT NULL DEFAULT '',
    plz              TEXT NOT NULL DEFAULT '',
    ort              TEXT NOT NULL DEFAULT '',
    email            TEXT NOT NULL DEFAULT '',
    telefon          TEXT NOT NULL DEFAULT '',
    notiz            TEXT NOT NULL DEFAULT '',
    aktiv            INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS leistungen (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    bezeichnung   TEXT NOT NULL,
    beschreibung  TEXT NOT NULL DEFAULT '',
    einheit       TEXT NOT NULL DEFAULT 'Stunde',
    preis         REAL NOT NULL DEFAULT 0.0,
    aktiv         INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS dokumente (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    art          TEXT NOT NULL CHECK (art IN ('angebot', 'rechnung')),
    nummer       TEXT NOT NULL,
    kunde_id     INTEGER REFERENCES kunden(id),
    datum        TEXT NOT NULL,
    gueltig_bis  TEXT NOT NULL DEFAULT '',
    faellig      TEXT NOT NULL DEFAULT '',
    notiz        TEXT NOT NULL DEFAULT '',
    eigener_text TEXT NOT NULL DEFAULT '',
    erstellt     TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS positionen (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    dokument_id  INTEGER NOT NULL REFERENCES dokumente(id) ON DELETE CASCADE,
    leistung_id  INTEGER REFERENCES leistungen(id),
    bezeichnung  TEXT NOT NULL,
    menge        REAL NOT NULL DEFAULT 1.0,
    einheit      TEXT NOT NULL DEFAULT '',
    preis        REAL NOT NULL DEFAULT 0.0,
    reihe        INTEGER NOT NULL DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS dokumente_nummer_eindeutig
    ON dokumente (art, nummer);
CREATE INDEX IF NOT EXISTS positionen_dokument ON positionen (dokument_id);
"""

#: Die Leistungen, die ein neues Tonstudio braucht. Sie werden nur angelegt,
#: wenn die Tabelle noch leer ist, damit vorhandene Preise unangetastet bleiben.
STARTLEISTUNGEN = [
    ("Aufnahme Ton", "Tag", 850.0),
    ("Mischung und Mastering", "Stunde", 95.0),
    ("Sprecherstimme", "Stunde", 120.0),
    ("Jingle / Sounddesign", "Stück", 450.0),
    ("Videomitschnitt aus Ton", "Stunde", 85.0),
]


def verbinden(pfad: Path | None = None) -> sqlite3.Connection:
    """Öffnet die Datenbank und legt das Schema an, falls es fehlt.

    Args:
        pfad: Eine andere Datei als ``~/.faktur/faktur.db``, für Tests.

    Returns:
        Die offene Verbindung mit aktivierten Fremdschlüsseln und
        zeilenweise Dict-Zugriff.
    """
    ziel = pfad or DATENBANK
    ziel.parent.mkdir(parents=True, exist_ok=True)

    verbindung = sqlite3.connect(ziel)
    verbindung.row_factory = sqlite3.Row
    verbindung.execute("PRAGMA foreign_keys = ON")
    verbindung.executescript(SCHEMA)

    if not verbindung.execute("SELECT 1 FROM leistungen LIMIT 1").fetchone():
        verbindung.executemany(
            "INSERT INTO leistungen (bezeichnung, einheit, preis) VALUES (?, ?, ?)",
            STARTLEISTUNGEN,
        )
        verbindung.commit()

    return verbindung


def ausgabeordner() -> Path:
    """Sorgt dafür, dass der Ordner für die PDF existiert.

    Returns:
        Der Pfad, in den die PDF geschrieben werden.
    """
    RECHNUNGEN.mkdir(parents=True, exist_ok=True)
    return RECHNUNGEN


def schliessen(verbindung: sqlite3.Connection) -> None:
    """Beendet alle offenen Transaktionen und schliesst die Verbindung.

    Args:
        verbindung: Die zu schliessende Verbindung.
    """
    verbindung.commit()
    verbindung.close()
