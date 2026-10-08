"""Wie eine Nummer auf dem Dokument aussieht.

Gespeichert sind vier Stellen: ``0032``. Was auf der PDF und im Dateinamen
steht, kann die Jahreszahl davor bekommen: ``2026-0032``.

**Die gespeicherte Nummer ändert sich nie.** Das ist der ganze Grund für
diese Trennung: Eine Rechnung ist schon verschickt, wenn ihre Nummer schon
gedruckt ist. Wer sie später umzählt, muss alle alten Belege anpassen — und
das lässt sich nicht mehr, sobald der erste beim Kunden liegt. Deshalb wird
das Jahr bei jedem Dokument aus dessen Datum gelesen, nicht in die Nummer
hineingerechnet.

Vier Stellen bleiben die Voreinstellung, weil die Anforderung von Anfang an
lautete, Nummern vierstellig zu führen.
"""

from __future__ import annotations

import sqlite3

#: Die Angebots- und Rechnungsnummer sind vier Stellen.
STELLEN = 4

#: Die möglichen Schreibweisen mit ihrer Bedeutung.
FORMATE = {
    "vierstellig": "Nur vier Stellen",
    "mit_jahr": "Mit der Jahreszahl",
}

#: Was ohne jede Einstellung gilt.
STANDARD = "vierstellig"

#: Der Einstellungsschlüssel.
SCHLUESSEL = "nummern_format"


def gewaehlt(db: sqlite3.Connection) -> str:
    """Liest die gewünschte Schreibweise.

    Args:
        db: Die Datenbankverbindung.

    Returns:
        ``vierstellig`` oder ``mit_jahr``.
    """
    from faktur import einstellungen

    wert = einstellungen.hole(db, SCHLUESSEL, STANDARD).strip().lower()
    return wert if wert in FORMATE else STANDARD


def mit_jahr(db: sqlite3.Connection) -> bool:
    """Sagt, ob die Jahreszahl davor stehen soll.

    Args:
        db: Die Datenbankverbindung.

    Returns:
        ``True``, wenn das Jahr mitgedruckt wird.
    """
    return gewaehlt(db) == "mit_jahr"


def jahr_aus(datum: str) -> str:
    """Holt die vierstellige Jahreszahl aus einem Datum.

    Das Datum kann in irgendeiner Schreibweise dastehen, weil es so
    gespeichert wurde, wie es getippt wurde.

    Args:
        datum: Das Datum in irgendeiner lesbaren Form.

    Returns:
        Die Jahreszahl, oder ``""``, wenn kein Datum erkannt wurde.
    """
    from faktur import betraege

    gefunden = betraege.lies_datum(datum)
    return gefunden.strftime("%Y") if gefunden else ""


def anzeige(nummer: str, datum: str, mit_jahr_wahl: bool = False) -> str:
    """Baut die Nummer, wie sie auf dem Dokument steht.

    Args:
        nummer: Die gespeicherte Nummer, etwa ``0032``.
        datum: Das Datum des Dokuments, falls die Jahreszahl gewünscht ist.
        mit_jahr_wahl: Ob die Jahreszahl davor stehen soll.

    Returns:
        ``0032`` oder ``2026-0032``. Ohne erkennbares Datum bleibt es bei
        der reinen Nummer, damit keine halbe Jahreszahl dasteht.
    """
    nummer = nummer.strip()

    if not mit_jahr_wahl:
        return nummer

    jahr = jahr_aus(datum)
    return f"{jahr}-{nummer}" if jahr else nummer
