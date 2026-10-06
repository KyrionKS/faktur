"""Stammdaten, Logo und Textbausteine.

Die Stammdaten stehen als einfache Schlüssel-Wert-Paare in der Datenbank.
Wer sie noch nicht eingetragen hat, bekommt beim Start einen Hinweis, aber
kein Absturz: die App ist auch ohne Stammdaten bedienbar.
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from faktur.db import DATENORDNER, STANDARD_LOGO

#: Die Felder der Stammdaten in der Reihenfolge des Formulars.
FELDER = (
    ("firma", "Firmenname"),
    ("zusatz", "Zusatz zur Firma"),
    ("strasse", "Strasse"),
    ("plz", "PLZ"),
    ("ort", "Ort"),
    ("telefon", "Telefon"),
    ("email", "E-Mail"),
    ("webseite", "Webseite"),
    ("bank", "Bank"),
    ("iban", "IBAN"),
    ("bic", "BIC"),
    ("steuernummer", "Steuernummer"),
    ("inhaber", "Inhaber"),
)

#: Was in den Textbausteinen ersetzt werden kann, mit Beispiel.
PLATZHALTER = {
    "Kunde": "Soundcheck GmbH",
    "Kunde_Anrede": "Herr Mustermann",
    "Ansprechpartner": "Max Mustermann",
    "Nummer": "2026-014",
    "Datum": "06.10.2026",
    "Faellig": "20.10.2026",
    "Gueltig_bis": "27.10.2026",
    "Betrag": "3.290,00 €",
    "Anzahl_Positionen": "2",
    "EigeneFirma": "New Air Media Group",
    "EigeneFirma_voll": "New Air Media Group, Tonstudio & Medienproduktion",
    "Bank": "Deutsche Kreditbank",
    "IBAN": "DE02 1203 0000 0000 2020 51",
}

#: Der Vorschlag, wenn noch kein Baustein gespeichert ist.
BAUSTEINE_VORSCHLAG = {
    "text_angebot": (
        "Hallo {{Kunde_Anrede}},\n\nvielen Dank für Ihre Anfrage! Anbei finden "
        "Sie unser Angebot.\nWir freuen uns auf die Zusammenarbeit mit Ihnen.\n\n"
        "Ihre Fragen beantwortet gerne {{EigeneFirma}}.\n\n"
        "Freundliche Grüße\n{{EigeneFirma}}"
    ),
    "text_rechnung": (
        "Hallo {{Kunde_Anrede}},\n\nvielen Dank! Anbei erhalten Sie Ihre "
        "Rechnung.\nBei Fragen erreichen Sie uns jederzeit.\n\n"
        "Viel Erfolg mit dem Projekt!\n\nFreundliche Grüße\n{{EigeneFirma}}"
    ),
}


def hole(db: sqlite3.Connection, schluessel: str, vorschlag: str = "") -> str:
    """Liest eine Einstellung.

    Args:
        db: Die Datenbankverbindung.
        schluessel: Der Name der Einstellung.
        vorschlag: Was geliefert wird, wenn nichts gespeichert ist.

    Returns:
        Der gespeicherte Wert oder der Vorschlag.
    """
    zeile = db.execute(
        "SELECT wert FROM einstellungen WHERE schluessel = ?", (schluessel,)
    ).fetchone()
    if zeile is None:
        return vorschlag
    return zeile["wert"] or vorschlag


def speichere(db: sqlite3.Connection, schluessel: str, wert: str) -> None:
    """Schreibt eine Einstellung, legt sie an, wenn sie fehlt.

    Args:
        db: Die Datenbankverbindung.
        schluessel: Der Name der Einstellung.
        wert: Der Wert. Leer ist erlaubt.
    """
    db.execute(
        "INSERT INTO einstellungen (schluessel, wert) VALUES (?, ?)"
        " ON CONFLICT(schluessel) DO UPDATE SET wert = excluded.wert",
        (schluessel, wert),
    )
    db.commit()


def alle(db: sqlite3.Connection) -> dict[str, str]:
    """Gibt alle Stammdaten als Dictionary zurück.

    Args:
        db: Die Datenbankverbindung.

    Returns:
        Die gespeicherten Werte. Fehlende Felder sind nicht enthalten.
    """
    return {
        zeile["schluessel"]: zeile["wert"]
        for zeile in db.execute("SELECT schluessel, wert FROM einstellungen")
    }


def fehlend(db: sqlite3.Connection) -> list[str]:
    """Sucht die Stammdaten, die noch fehlen.

    Args:
        db: Die Datenbankverbindung.

    Returns:
        Die Namen der Felder ohne Inhalt, in Formularreihenfolge.
    """
    daten = alle(db)
    return [
        schluessel for schluessel, _ in FELDER if not daten.get(schluessel, "").strip()
    ]


def vollstaendig(db: sqlite3.Connection) -> bool:
    """Sagt, ob die wichtigsten Stammdaten da sind.

    Args:
        db: Die Datenbankverbindung.

    Returns:
        ``True``, wenn Firma und IBAN eingetragen sind.
    """
    daten = alle(db)
    return bool(daten.get("firma", "").strip()) and bool(daten.get("iban", "").strip())


def baustein(db: sqlite3.Connection, art: str) -> str:
    """Liest den Brieftext für eine Dokumentart.

    Args:
        db: Die Datenbankverbindung.
        art: ``angebot`` oder ``rechnung``.

    Returns:
        Der Baustein, oder der Vorschlag, wenn noch keiner gespeichert ist.
    """
    return hole(
        db,
        f"text_{art}",
        BAUSTEINE_VORSCHLAG.get(f"text_{art}", ""),
    )


def logo_pfad(db: sqlite3.Connection) -> Path | None:
    """Sucht die Logodatei.

    Erst der in den Einstellungen genannte Pfad, dann der Standard im
    Datenordner.

    Args:
        db: Die Datenbankverbindung.

    Returns:
        Der Pfad zur Datei, oder ``None``, wenn keine existiert.
    """
    eigener = hole(db, "logo_pfad").strip()
    kandidaten = [Path(eigener).expanduser()] if eigener else []
    kandidaten += [STANDARD_LOGO, DATENORDNER / "logo.png"]

    for kandidat in kandidaten:
        if kandidat.is_file():
            return kandidat
    return None


def logo_uebernehmen(db: sqlite3.Connection, quelle: Path) -> Path:
    """Kopiert ein Logo in den Datenordner und merkt sich den Pfad.

    Args:
        db: Die Datenbankverbindung.
        quelle: Die Bilddatei.

    Returns:
        Der Pfad im Datenordner.

    Raises:
        FileNotFoundError: Wenn die Quelldatei fehlt.
    """
    if not quelle.is_file():
        raise FileNotFoundError(f"Keine Datei gefunden: {quelle}")

    DATENORDNER.mkdir(parents=True, exist_ok=True)
    ziel = DATENORDNER / "logo.png"
    shutil.copyfile(quelle, ziel)
    speichere(db, "logo_pfad", str(ziel))
    return ziel
