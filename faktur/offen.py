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

    **Beide Daten erst gelesen, dann verglichen.** In der Datenbank steht
    es als ``TT.MM.JJJJ``, und als Text verglichen stimmt sich das nur
    innerhalb desselben Jahres: „05.11.2026" ist kleiner als „15.10.2026",
    weil 0 kleiner ist als 1 — obwohl der 5. November später liegt.

    **Auch ``heute`` wird gelesen.** Vorher stand hier
    ``gefunden.isoformat() < heute``: links stand ein Datum in ISO, rechts
    eines in deutscher Schreibweise, und der Vergleich war ein Vergleich
    zweier Varioussprachen. „2020-01-01" gegen „15.10.2026" — die erste
    Zahl beginnt mit 2, die zweite mit 1, also war die Frist praktisch nie
    abgelaufen. Im Bild stand darum so gut wie nie *überfällig*, und die
    Seite *Offene Forderungen* hatte die dringenden Fälle nicht zu zeigen.
    Der Test daneben bestand, weil er ``heute`` in ISO übergab — ein
    Format, das der einzige Aufrufer im Programm nie benutzt.

    Args:
        dokument: Das Dokument mit ``faellig`` und ``bezahlt_am``.
        heute: Das heutige Datum. Wie :func:`faktur.betraege.datum` es
            schreibt, also ``TT.MM.JJJJ``. ISO geht auch.

    Returns:
        ``True``, wenn die Frist abgelaufen und nichts bezahlt wurde.
    """
    if not ist_offen(dokument):
        return False

    frist = (dokument["faellig"] or "").strip()
    if not frist:
        return False

    # Beide Seiten durch denselben Parser. Was nicht lesbar ist, gilt
    # nicht als überfaellig — lieber zuwenig melden als einen Kunden
    # mahnen, dem nichts zu zahlen fällig ist.
    from faktur import betraege

    gefunden = betraege.lies_datum(frist)
    wann = betraege.lies_datum(heute)
    if gefunden is None or wann is None:
        return False

    return gefunden < wann


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


def summe_ueberfaellig(db: sqlite3.Connection) -> float:
    """Rechnet die überfälligen Forderungen zusammen.

    :func:`summe_offen` zählt *jede* offene Rechnung. Diese zählt nur die,
    deren Frist abgelaufen ist — und das ist eine andere Zahl mit einer
    anderen Bedeutung. Auf der Übersicht stehen beide nebeneinander, weil
    eine davon sagt, was da ist, und die andere, was dringend ist.

    Args:
        db: Die Datenbankverbindung.

    Returns:
        Die Summe der überfälligen Rechnungen.
    """
    from faktur import betraege, dateien

    heute = betraege.heute()
    return sum(
        dateien.summe_von(db, int(dokument["id"]))
        for dokument in offene(db)
        if ist_faellig(dokument, heute)
    )
