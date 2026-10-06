"""Schema und Verbindung zur Datenbank.

Die Daten liegen in einer SQLite-Datei neben dem Programm, in ``daten/``.
Das ist Absicht: der ganze Bestand an Kunden, Angeboten und Rechnungen steht
in einem Ordner, der sich kopieren, verschieben oder sichern lässt, ohne
dass man wissen muss, wo das Programm überall auf der Platte liegt.

    daten/
      faktur.db
      logo.png
      Dokumente/
        ANG - 0001 - Soundcheck GmbH.pdf

Früher lagen Datenbank und Dokumente an zwei verschiedenen Stellen im
Heimverzeichnis. Beim ersten Start wird eine solche Datei hierher verschoben,
damit die vorhandenen Kunden und Preise nicht verloren gehen.
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

#: Der Ordner neben dem Programm, in dem alles liegt.
DATENORDNER = Path(__file__).resolve().parent.parent / "daten"

#: Die Datenbank selbst.
DATENBANK = DATENORDNER / "faktur.db"

#: Das Logo fuer die PDF, falls in den Einstellungen keines liegt.
STANDARD_LOGO = DATENORDNER / "logo.png"

#: Der Ordner, in den die PDF geschrieben werden.
DOKUMENTE = DATENORDNER / "Dokumente"

#: Wo vor dem Umstieg die Daten lagen. Beim ersten Start wird von dort
#: hierher verschoben, damit die vorhandenen Kunden und Preise nicht
#: verloren gehen.
ALT_DATENORDNER = Path.home() / ".faktur"
ALT_DOKUMENTE = Path.home() / "Rechnungen"

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

CREATE INDEX IF NOT EXISTS positionen_dokument ON positionen (dokument_id);
"""

#: Der Index auf die Nummer steht nicht im Schema, weil er beim Umstieg von
#: ``(art, nummer)`` auf ``nummer`` ausgetauscht werden muss. SQLite kann
#: einen Index nicht umdeuten, nur fallen lassen und neu anlegen.
#:
#: Der Zähler läuft für Angebote und Rechnungen zusammen. Deshalb muss die
#: Nummer allein eindeutig sein, sonst dürfte ein Angebot und eine Rechnung
#: dieselbe Nummer tragen und nichts wäre mehr durchgängig zu lesen.

#: Wie viele Stellen eine Dokumentnummer hat.
NUMMER_STELLEN = 4

#: Die Schemastufe, auf der die Datei heute steht. Sie wird hochgezählt,
#: damit die zugehörige Wanderung genau einmal läuft.
SCHEMA_STUFE = 2

#: Der Name des Eintrags, in dem die Schemastufe steht.
SCHLUESSEL_STUFE = "schema_stufe"

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
    """Öffnet die Datenbank und bringt sie auf den heutigen Stand.

    Das Schema wird ergänzt, eine ältere Datei wird einmal umgeschrieben, und
    die Startleistungen kommen nur in eine leere Liste. Die Sicherungskopie
    entsteht nur, wenn wirklich umgeschrieben wird.

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

    _wandern(verbindung, ziel)
    _indizes_setzen(verbindung)
    _startleistungen(verbindung)

    return verbindung


def _startleistungen(verbindung: sqlite3.Connection) -> None:
    """Legt die Leistungen des Tonstudios an, wenn die Liste leer ist.

    Nur beim ersten Mal. Danach bleiben die Preise, wie sie sind.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    if verbindung.execute("SELECT 1 FROM leistungen LIMIT 1").fetchone():
        return

    verbindung.executemany(
        "INSERT INTO leistungen (bezeichnung, einheit, preis) VALUES (?, ?, ?)",
        STARTLEISTUNGEN,
    )
    verbindung.commit()


def _wandern(verbindung: sqlite3.Connection, pfad: Path) -> None:
    """Bringt eine ältere Datei auf den heutigen Stand.

    Args:
        verbindung: Die Datenbankverbindung.
        pfad: Die Datei, um die es geht.
    """
    if _stufe(verbindung) >= SCHEMA_STUFE:
        return

    if verbindung.execute("SELECT COUNT(*) AS anzahl FROM dokumente").fetchone()[
        "anzahl"
    ]:
        # Erst sichern, dann umschreiben. Die alte Datei bleibt liegen, falls
        # jemand doch noch nachsehen will, wie die Nummern vorher waren.
        shutil.copy2(pfad, pfad.with_suffix(pfad.suffix + ".bak"))
        _nummern_umerodieren(verbindung)

    verbindung.execute(
        "INSERT INTO einstellungen (schluessel, wert) VALUES (?, ?)"
        " ON CONFLICT(schluessel) DO UPDATE SET wert = excluded.wert",
        (SCHLUESSEL_STUFE, str(SCHEMA_STUFE)),
    )
    verbindung.commit()


def _stufe(verbindung: sqlite3.Connection) -> int:
    """Liest die Schemastufe aus der Datenbank.

    Args:
        verbindung: Die Datenbankverbindung.

    Returns:
        Die Stufe. Eine frische Datei hat noch keine und bekommt 1.
    """
    zeile = verbindung.execute(
        "SELECT wert FROM einstellungen WHERE schluessel = ?", (SCHLUESSEL_STUFE,)
    ).fetchone()
    if zeile and zeile["wert"].isdigit():
        return int(zeile["wert"])
    return 1


def _nummern_umerodieren(verbindung: sqlite3.Connection) -> None:
    """Schreibt alle Dokumentnummern auf vier Stellen um.

    Sortiert wird nach Datum, dann nach Anlagereihe. So bekommt das älteste
    Dokument die kleinste Nummer und Angebot und Rechnung eines Vorgangs
    stehen nebeneinander. Die Positionen bleiben, weil nur die Nummer in
    ``dokumente`` angefasst wird.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    zeilen = verbindung.execute(
        "SELECT id FROM dokumente ORDER BY datum, id"
    ).fetchall()

    for zaehler, zeile in enumerate(zeilen, start=1):
        verbindung.execute(
            "UPDATE dokumente SET nummer = ? WHERE id = ?",
            (nummer_aus(zaehler), zeile["id"]),
        )


def _indizes_setzen(verbindung: sqlite3.Connection) -> None:
    """Sorgt für den richtigen Index auf der Dokumentnummer.

    Die Nummer muss für sich allein eindeutig sein, weil Angebot und
    Rechnung aus einem Zähler kommen. Ein alter Index auf ``(art, nummer)``
    würde das noch zulassen, also wird er ersetzt.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    verbindung.execute("DROP INDEX IF EXISTS dokumente_nummer_eindeutig")
    verbindung.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS dokumente_nummer_eindeutig"
        " ON dokumente (nummer)"
    )
    verbindung.commit()


def nummer_aus(zahl: int) -> str:
    """Formatiert eine Zahl als Dokumentnummer.

    Args:
        zahl: Die laufende Nummer, beginnend bei 1.

    Returns:
        Die Nummer mit führenden Nullen, etwa ``0001``.
    """
    return f"{zahl:0{NUMMER_STELLEN}d}"


def ausgabeordner() -> Path:
    """Sorgt dafür, dass der Ordner für die PDF existiert.

    Angebot und Rechnung liegen im selben Ordner. Welche es ist, steht im
    Dateinamen: ``ANG - 0001 - …`` und ``RE - 0002 - …``.

    Returns:
        Der Pfad, in den die PDF geschrieben werden.
    """
    DOKUMENTE.mkdir(parents=True, exist_ok=True)
    return DOKUMENTE


def umziehen() -> list[str]:
    """Bringt eine ältere Datei an den heutigen Ort.

    Vorher lagen die Daten in ``~/.faktur`` und die PDF in
    ``~/Rechnungen``. Beides wird hierher verschoben, nicht kopiert, damit
    an der alten Stelle nichts zurückbleibt, das auseinanderläuft.

    Verschoben wird nur, was noch nicht da ist. Läuft die App zweimal, ist
    beim zweiten Mal nichts zu tun. Die beiden alten Orte werden einzeln
    geprüft, denn es kann sein, dass es nur einen davon noch gibt.

    Returns:
        Die Meldungen für den Benutzer, eine je verschobener Sache.
    """
    meldungen: list[str] = []

    if ALT_DATENORDNER.is_dir():
        DATENORDNER.mkdir(parents=True, exist_ok=True)
        meldungen += _umziehen_aus(ALT_DATENORDNER)

    if ALT_DOKUMENTE.is_dir() and any(ALT_DOKUMENTE.glob("*.pdf")):
        DOKUMENTE.mkdir(parents=True, exist_ok=True)
        for pdf in sorted(ALT_DOKUMENTE.glob("*.pdf")):
            ziel = DOKUMENTE / pdf.name
            if ziel.exists():
                continue
            shutil.move(str(pdf), str(ziel))
            meldungen.append(f"{pdf.name} nach Dokumente/ verschoben")

    return meldungen


def _umziehen_aus(quelle: Path) -> list[str]:
    """Verschiebt die Dateien eines alten Datenordners.

    Args:
        quelle: Der alte Ordner.

    Returns:
        Die Meldungen für den Benutzer.
    """
    meldungen: list[str] = []

    alt = quelle / DATENBANK.name
    if alt.is_file() and not DATENBANK.exists():
        shutil.move(str(alt), str(DATENBANK))
        meldungen.append("Datenbank übernommen")

    for name in ("logo.png", "faktur.db.bak"):
        quelle_datei = quelle / name
        if quelle_datei.is_file() and not (DATENORDNER / name).exists():
            shutil.move(str(quelle_datei), str(DATENORDNER / name))
            meldungen.append(f"{name} übernommen")

    return meldungen


def schliessen(verbindung: sqlite3.Connection) -> None:
    """Beendet alle offenen Transaktionen und schliesst die Verbindung.

    Args:
        verbindung: Die zu schliessende Verbindung.
    """
    verbindung.commit()
    verbindung.close()
