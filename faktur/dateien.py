"""Lesen und Schreiben von Kunden, Leistungen und Dokumenten.

Hier steht alles, was mit der Datenbank zu tun hat. Die Textual-Oberfläche
kennt diese Functionsnamen nicht, sie fragt nur danach.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence

from faktur.db import nummer_aus

#: Die Spalten eines Kunden, in der Reihenfolge des Formulars.
KUNDENFELDER = (
    "firma",
    "ansprechpartner",
    "strasse",
    "plz",
    "ort",
    "email",
    "telefon",
    "notiz",
)


# ---------------------------------------------------------------- Kunden


def kunden(db: sqlite3.Connection, nur_aktive: bool = False) -> list[sqlite3.Row]:
    """Gibt alle Kunden zurück, nach Firma sortiert.

    Args:
        db: Die Datenbankverbindung.
        nur_aktive: Wenn wahr, kommen inaktive Kunden nicht mit.

    Returns:
        Die Kunden, alphabetisch nach Firma.
    """
    where = " WHERE aktiv = 1" if nur_aktive else ""
    return list(
        db.execute(f"SELECT * FROM kunden{where} ORDER BY firma COLLATE NOCASE")
    )


def kunde_holen(db: sqlite3.Connection, kunde_id: int) -> sqlite3.Row | None:
    """Holt einen Kunden nach seiner Nummer.

    Args:
        db: Die Datenbankverbindung.
        kunde_id: Die Nummer des Kunden.

    Returns:
        Der Kunde, oder ``None``, wenn es ihn nicht gibt.
    """
    return db.execute("SELECT * FROM kunden WHERE id = ?", (kunde_id,)).fetchone()


def kunde_speichern(
    db: sqlite3.Connection, daten: dict[str, str], kunde_id: int | None = None
) -> int:
    """Legt einen Kunden an oder ändert einen bestehenden.

    Args:
        db: Die Datenbankverbindung.
        daten: Die Felder aus :data:`KUNDENFELDER`.
        kunde_id: Die Nummer beim Ändern, ``None`` beim Anlegen.

    Returns:
        Die Nummer des gespeicherten Kunden.
    """
    werte = [daten.get(feld, "").strip() for feld in KUNDENFELDER]
    spalten = ", ".join(KUNDENFELDER)
    platzhalter = ", ".join("?" * len(KUNDENFELDER))

    if kunde_id is None:
        cursor = db.execute(
            f"INSERT INTO kunden ({spalten}) VALUES ({platzhalter})", werte
        )
        neu = cursor.lastrowid or 0
    else:
        zuweisung = ", ".join(f"{feld} = ?" for feld in KUNDENFELDER)
        db.execute(f"UPDATE kunden SET {zuweisung} WHERE id = ?", [*werte, kunde_id])
        neu = kunde_id

    db.commit()
    return neu


def kunde_loeschen(db: sqlite3.Connection, kunde_id: int) -> None:
    """Löscht einen Kunden samt seiner Dokumente.

    Args:
        db: Die Datenbankverbindung.
        kunde_id: Die Nummer des Kunden.
    """
    dokumente = [
        zeile["id"]
        for zeile in db.execute(
            "SELECT id FROM dokumente WHERE kunde_id = ?", (kunde_id,)
        )
    ]
    for dokument_id in dokumente:
        db.execute("DELETE FROM positionen WHERE dokument_id = ?", (dokument_id,))
    db.execute("DELETE FROM dokumente WHERE kunde_id = ?", (kunde_id,))
    db.execute("DELETE FROM kunden WHERE id = ?", (kunde_id,))
    db.commit()


# ------------------------------------------------------------- Leistungen


def leistungen(db: sqlite3.Connection, nur_aktive: bool = False) -> list[sqlite3.Row]:
    """Gibt die Preisliste zurück, nach Bezeichnung sortiert.

    Args:
        db: Die Datenbankverbindung.
        nur_aktive: Wenn wahr, kommen inaktive Leistungen nicht mit.

    Returns:
        Die Leistungen, alphabetisch nach Bezeichnung.
    """
    where = " WHERE aktiv = 1" if nur_aktive else ""
    return list(
        db.execute(
            f"SELECT * FROM leistungen{where} ORDER BY bezeichnung COLLATE NOCASE"
        )
    )


def leistung_holen(db: sqlite3.Connection, leistung_id: int) -> sqlite3.Row | None:
    """Holt eine Leistung nach ihrer Nummer.

    Args:
        db: Die Datenbankverbindung.
        leistung_id: Die Nummer der Leistung.

    Returns:
        Die Leistung, oder ``None``.
    """
    return db.execute(
        "SELECT * FROM leistungen WHERE id = ?", (leistung_id,)
    ).fetchone()


def leistung_speichern(
    db: sqlite3.Connection,
    daten: dict[str, str | float],
    leistung_id: int | None = None,
) -> int:
    """Legt eine Leistung an oder ändert eine bestehende.

    Args:
        db: Die Datenbankverbindung.
        daten: ``bezeichnung``, ``beschreibung``, ``einheit`` und ``preis``.
        leistung_id: Die Nummer beim Ändern, ``None`` beim Anlegen.

    Returns:
        Die Nummer der gespeicherten Leistung.
    """
    bezeichnung = str(daten.get("bezeichnung", "")).strip()
    beschreibung = str(daten.get("beschreibung", "")).strip()
    einheit = str(daten.get("einheit", "Stunde")).strip() or "Stunde"

    from faktur.betraege import zahl

    preis = zahl(daten.get("preis", 0.0))

    if leistung_id is None:
        cursor = db.execute(
            "INSERT INTO leistungen (bezeichnung, beschreibung, einheit, preis)"
            " VALUES (?, ?, ?, ?)",
            (bezeichnung, beschreibung, einheit, preis),
        )
        neu = cursor.lastrowid or 0
    else:
        db.execute(
            "UPDATE leistungen SET bezeichnung = ?, beschreibung = ?,"
            " einheit = ?, preis = ? WHERE id = ?",
            (bezeichnung, beschreibung, einheit, preis, leistung_id),
        )
        neu = leistung_id

    db.commit()
    return neu


def leistung_loeschen(db: sqlite3.Connection, leistung_id: int) -> None:
    """Nimmt eine Leistung aus der Preisliste.

    Positionen auf alten Dokumenten bleiben erhalten, weil dort der Text und
    der Preis mitgeschrieben sind. Nur die Verknüpfung verschwindet.

    Args:
        db: Die Datenbankverbindung.
        leistung_id: Die Nummer der Leistung.
    """
    db.execute(
        "UPDATE positionen SET leistung_id = NULL WHERE leistung_id = ?",
        (leistung_id,),
    )
    db.execute("DELETE FROM leistungen WHERE id = ?", (leistung_id,))
    db.commit()


# -------------------------------------------------------------- Dokumente


def dokumente(db: sqlite3.Connection, art: str | None = None) -> list[sqlite3.Row]:
    """Gibt die Dokumente zurück, neueste zuerst.

    Args:
        db: Die Datenbankverbindung.
        art: Nur Angebote oder nur Rechnungen, sonst alles.

    Returns:
        Die Dokumente mit dem Namen des Kunden im Feld ``firma``.
    """
    where = " WHERE d.art = ?" if art else ""
    werte: tuple[str, ...] = (art,) if art else ()
    return list(
        db.execute(
            """
            SELECT d.*, COALESCE(k.firma, '(kein Kunde)') AS firma
            FROM dokumente AS d
            LEFT JOIN kunden AS k ON k.id = d.kunde_id
            """
            f"{where}"
            " ORDER BY d.datum DESC, d.id DESC",
            werte,
        )
    )


def dokument_holen(db: sqlite3.Connection, dokument_id: int) -> sqlite3.Row | None:
    """Holt ein Dokument nach seiner Nummer.

    Args:
        db: Die Datenbankverbindung.
        dokument_id: Die Nummer des Dokuments.

    Returns:
        Das Dokument, oder ``None``.
    """
    return db.execute(
        """
        SELECT d.*, COALESCE(k.firma, '') AS firma,
               k.ansprechpartner, k.strasse, k.plz, k.ort, k.email, k.telefon
        FROM dokumente AS d
        LEFT JOIN kunden AS k ON k.id = d.kunde_id
        WHERE d.id = ?
        """,
        (dokument_id,),
    ).fetchone()


def positionen(db: sqlite3.Connection, dokument_id: int) -> list[sqlite3.Row]:
    """Gibt die Positionen eines Dokuments in Reihenfolge zurück.

    Args:
        db: Die Datenbankverbindung.
        dokument_id: Die Nummer des Dokuments.

    Returns:
        Die Positionen, von oben nach unten.
    """
    return list(
        db.execute(
            "SELECT * FROM positionen WHERE dokument_id = ? ORDER BY reihe, id",
            (dokument_id,),
        )
    )


def summe_von(db: sqlite3.Connection, dokument_id: int) -> float:
    """Rechnet die Summe eines Dokuments aus.

    Args:
        db: Die Datenbankverbindung.
        dokument_id: Die Nummer des Dokuments.

    Returns:
        Die Summe aus Menge mal Preis aller Positionen.
    """
    zeile = db.execute(
        "SELECT COALESCE(SUM(menge * preis), 0) AS summe"
        " FROM positionen WHERE dokument_id = ?",
        (dokument_id,),
    ).fetchone()
    return float(zeile["summe"])


def nummern(db: sqlite3.Connection) -> list[str]:
    """Gibt alle vergebenen Dokumentnummern zurück.

    Angebot und Rechnung kommen aus einem Zähler, deshalb wird nicht nach
    Art gefiltert. Nur so lässt sich prüfen, ob eine Nummer wirklich frei ist.

    Args:
        db: Die Datenbankverbindung.

    Returns:
        Die Nummern als Liste.
    """
    return [
        zeile["nummer"]
        for zeile in db.execute("SELECT nummer FROM dokumente WHERE nummer <> ''")
    ]


def naechste_nummer(db: sqlite3.Connection) -> str:
    """Schlägt die nächste freie Dokumentnummer vor.

    Args:
        db: Die Datenbankverbindung.

    Returns:
        Die Nummer mit führenden Nullen, etwa ``0003``. Bei einer leeren
        Liste beginnt der Zähler bei ``0001``.
    """
    hoechste = 0
    for nummer in nummern(db):
        if nummer.isdigit():
            hoechste = max(hoechste, int(nummer))
    return nummer_aus(hoechste + 1)


def dokument_speichern(
    db: sqlite3.Connection,
    kopf: dict[str, str | int | None],
    positionen_liste: Sequence[dict[str, str | float | int | None]],
) -> int:
    """Legt ein Dokument mit seinen Positionen an oder ändert es.

    Args:
        db: Die Datenbankverbindung.
        kopf: ``art``, ``nummer``, ``kunde_id``, ``datum``, ``gueltig_bis``,
            ``faellig``, ``notiz``, ``eigener_text`` und optional
            ``dokument_id``.
        positionen_liste: Die Positionen mit ``bezeichnung``, ``menge``,
            ``einheit``, ``preis`` und optional ``leistung_id``.

    Returns:
        Die Nummer des gespeicherten Dokuments.

    Raises:
        sqlite3.IntegrityError: Wenn die Nummer schon vergeben ist. Angebot
            und Rechnung kommen aus einem Zähler, die Nummer muss für sich
            allein eindeutig sein.
    """
    from faktur.betraege import zahl

    dokument_id = kopf.get("dokument_id")
    werte = (
        str(kopf.get("art", "angebot")),
        str(kopf.get("nummer", "")).strip(),
        kopf.get("kunde_id"),
        str(kopf.get("datum", "")),
        str(kopf.get("gueltig_bis", "")),
        str(kopf.get("faellig", "")),
        str(kopf.get("notiz", "")),
        str(kopf.get("eigener_text", "")),
    )

    if dokument_id is None:
        cursor = db.execute(
            "INSERT INTO dokumente"
            " (art, nummer, kunde_id, datum, gueltig_bis, faellig, notiz,"
            "  eigener_text)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            werte,
        )
        neu = cursor.lastrowid or 0
    else:
        zuweisung = (
            "art = ?, nummer = ?, kunde_id = ?, datum = ?, gueltig_bis = ?,"
            " faellig = ?, notiz = ?, eigener_text = ?"
        )
        db.execute(
            f"UPDATE dokumente SET {zuweisung} WHERE id = ?", [*werte, dokument_id]
        )
        neu = int(dokument_id)

    # Die Positionen werden jedes Mal neu geschrieben. Sie sind klein, und so
    # kann keine halb gelöschte Liste zurückbleiben.
    db.execute("DELETE FROM positionen WHERE dokument_id = ?", (neu,))
    for nummer, position in enumerate(positionen_liste):
        db.execute(
            "INSERT INTO positionen"
            " (dokument_id, leistung_id, bezeichnung, menge, einheit, preis, reihe)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                neu,
                position.get("leistung_id"),
                str(position.get("bezeichnung", "")),
                zahl(position.get("menge", 1.0)),
                str(position.get("einheit", "")),
                zahl(position.get("preis", 0.0)),
                nummer,
            ),
        )

    db.commit()
    return neu


def dokument_loeschen(db: sqlite3.Connection, dokument_id: int) -> None:
    """Löscht ein Dokument samt seiner Positionen.

    Args:
        db: Die Datenbankverbindung.
        dokument_id: Die Nummer des Dokuments.
    """
    db.execute("DELETE FROM positionen WHERE dokument_id = ?", (dokument_id,))
    db.execute("DELETE FROM dokumente WHERE id = ?", (dokument_id,))
    db.commit()


def als_angebot_uebernehmen(
    db: sqlite3.Connection, dokument_id: int
) -> tuple[dict[str, str | int | None], list[dict[str, str | float | int | None]]]:
    """Liest ein Dokument und macht daraus den Kopf einer Rechnung.

    Die Positionen werden mitgegeben, inklusive der Verknüpfung zur
    Leistung, damit der Preisliste wieder zugeordnet werden kann.

    Args:
        db: Die Datenbankverbindung.
        dokument_id: Die Nummer des Angebots.

    Returns:
        Ein Paar aus Kopfdaten und Positionen, bereit zum Speichern als
        Rechnung.

    Raises:
        ValueError: Wenn das Dokument keine Rechnung werden kann.
    """
    dokument = dokument_holen(db, dokument_id)
    if dokument is None:
        raise ValueError("Das Dokument gibt es nicht mehr.")
    if dokument["art"] != "angebot":
        raise ValueError("Nur aus einem Angebot lässt sich eine Rechnung machen.")

    kopf: dict[str, str | int | None] = {
        "art": "rechnung",
        "nummer": "",
        "kunde_id": dokument["kunde_id"],
        "datum": "",
        "faellig": "",
        "notiz": dokument["notiz"],
        "eigener_text": "",
    }

    liste: list[dict[str, str | float | int | None]] = []
    for position in positionen(db, dokument_id):
        liste.append(
            {
                "leistung_id": position["leistung_id"],
                "bezeichnung": position["bezeichnung"],
                "menge": position["menge"],
                "einheit": position["einheit"],
                "preis": position["preis"],
            }
        )

    return kopf, liste
