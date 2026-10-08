"""Offene Forderungen.

Wer nebenbei Rechnungen schreibt, will vor allem eine Zahl wissen: Was ist
noch offen? Nicht, weil er mahnen will — Mahnwesen ist bewusst nicht
dabei — sondern weil eine unbeachtete Rechnung das teuerste Ergebnis
dieses Programms wäre.

Deshalb steht in jedem Dokument ein Feld ``bezahlt_am``. Leer heißt offen.
Ein Angebot kann nicht bezahlt sein, es wird ja gar nicht in Rechnung
gestellt; ein als bezahlt markiertes Angebot wäre ein Widerspruch, und der
wird hier verhindert statt nur verhindert werden dürfen.
"""

from __future__ import annotations

import sqlite3
from typing import Literal

#: Wie eine Rechnung aussehen kann.
Zustaende = Literal["offen", "bezahlt", "faellig"]


def ist_offen(dokument: sqlite3.Row) -> bool:
    """Sagt, ob auf ein Dokument noch Geld zu bekommen ist.

    Args:
        dokument: Das Dokument mit den Feldern ``art`` und ``bezahlt_am``.

    Returns:
        ``True`` bei einer offenen Rechnung. Ein Angebot ist nie offen, es
        ist ein Angebot.
    """
    return dokument["art"] == "rechnung" and not (dokument["bezahlt_am"] or "").strip()


def ist_bezahlt(dokument: sqlite3.Row) -> bool:
    """Sagt, ob eine Rechnung als bezahlt vermerkt ist.

    Args:
        dokument: Das Dokument.

    Returns:
        ``True``, wenn ein Zahlungsdatum steht.
    """
    return bool((dokument["bezahlt_am"] or "").strip())


def ist_faellig(dokument: sqlite3.Row, heute: str) -> bool:
    """Sagt, ob eine offene Rechnung überfaellig ist.

    Das Datum wird als Text verglichen. Beide liegen im Format
    ``JJJJ-MM-TT`` in der Datenbank, und das stimmt sich schneller und ohne
    Umweg über ein Objekt.

    Args:
        dokument: Das Dokument mit ``faellig`` und ``bezahlt_am``.
        heute: Das heutige Datum als ``JJJJ-MM-TT``.

    Returns:
        ``True``, wenn die Frist abgelaufen und nichts bezahlt wurde.
    """
    if not ist_offen(dokument):
        return False

    frist = (dokument["faellig"] or "").strip()
    if not frist:
        return False

    # Das Datum aus jeder Schreibweise auf ISO bringen, sonst stimmt der
    # Vergleich nicht. Was nicht lesbar ist, gilt nicht als überfaellig.
    from faktur import betraege

    gefunden = betraege.lies_datum(frist)
    if gefunden is None:
        return False

    return gefunden.isoformat() < heute


def offene(db: sqlite3.Connection) -> list[sqlite3.Row]:
    """Gibt alle offenen Rechnungen zurück, älteste zuerst.

    Die älteste zuerst, weil sie am dringendsten ist.

    Args:
        db: Die Datenbankverbindung.

    Returns:
        Die offenen Rechnungen.
    """
    return list(
        db.execute(
            """
            SELECT d.*, COALESCE(k.firma, '(kein Kunde)') AS firma
            FROM dokumente AS d
            LEFT JOIN kunden AS k ON k.id = d.kunde_id
            WHERE d.art = 'rechnung' AND d.bezahlt_am = ''
            ORDER BY d.faellig, d.datum, d.id
            """
        )
    )


def summe_offen(db: sqlite3.Connection) -> float:
    """Rechnet die offenen Forderungen zusammen.

    Args:
        db: Die Datenbankverbindung.

    Returns:
        Die Summe aller unbezahlten Rechnungen.
    """
    zeile = db.execute(
        """
        SELECT COALESCE(SUM(p.preis * p.menge), 0) AS summe
        FROM positionen AS p
        JOIN dokumente AS d ON d.id = p.dokument_id
        WHERE d.art = 'rechnung' AND d.bezahlt_am = ''
        """
    ).fetchone()

    return float(zeile["summe"]) if zeile else 0.0


def als_bezahlt_markieren(db: sqlite3.Connection, dokument_id: int, wann: str) -> bool:
    """Vermerkt eine Rechnung als bezahlt.

    Args:
        db: Die Datenbankverbindung.
        dokument_id: Welche Rechnung.
        wann: Das Datum als ``JJJJ-MM-TT``. Leer macht sie wieder offen.

    Returns:
        ``True``, wenn es geklappt hat. Bei einem Angebot nicht: Es gibt
        keinen Geldbetrag, den man einziehen könnte, und ein als bezahlt
        markiertes Angebot wäre eine Angabe, die nicht stimmt.
    """
    reihe = db.execute(
        "SELECT art FROM dokumente WHERE id = ?", (dokument_id,)
    ).fetchone()

    if reihe is None or reihe["art"] != "rechnung":
        return False

    db.execute(
        "UPDATE dokumente SET bezahlt_am = ? WHERE id = ?",
        (wann.strip(), dokument_id),
    )
    db.commit()
    return True
