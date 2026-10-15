"""Lesen und Schreiben von Kunden, Leistungen und Dokumenten.

Hier steht alles, was mit der Datenbank zu tun hat. Die Textual-Oberfläche
kennt diese Functionsnamen nicht, sie fragt nur danach.
"""

from __future__ import annotations

import datetime
import sqlite3
from collections.abc import Sequence
from typing import NamedTuple

from faktur import betraege
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


def dateiname(dokument: sqlite3.Row, art: str, nummer_text: str | None = None) -> str:
    """Baut den Dateinamen einer PDF.

    Angebot und Rechnung liegen im selben Ordner, die Art steht deshalb im
    Namen:

        ANG - 0199 - Tonstudio Nordwind
        RE - 0199 - Tonstudio Nordwind

    Beide tragen dieselbe Nummer, weil sie zum selben Projekt gehoeren. Genau
    das macht das Kuerzel ``ANG`` und ``RE`` noetig: Ohne sie hiessen die
    beiden Dateien gleich und die zweite wuerde die erste ersetzen.

    Args:
        dokument: Das Dokument.
        art: ``angebot`` oder ``rechnung``.
        nummer_text: Die Nummer, wie sie im Namen stehen soll. Ohne
            Angabe wird die gespeicherte genommen.

    Returns:
        Der Dateiname, ohne Ordner und ohne Endung.
    """
    kennung = "ANG" if art == "angebot" else "RE"
    nummer = _sicher(nummer_text or dokument["nummer"] or str(dokument["id"]))
    kunde = _sicher(dokument["firma"] or "ohne Kunde")
    return f"{kennung} - {nummer} - {kunde}"


def _sicher(text: str) -> str:
    """Entfernt die Zeichen, die im Dateinamen Ärger machen.

    Args:
        text: Der Name.

    Returns:
        Der Name ohne Schrägstriche, Doppelpunkte und Rückschritte.
    """
    for zeichen in '/\\:*?"<>|':
        text = text.replace(zeichen, "-")
    return " ".join(text.split())


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
            ``faellig``, ``notiz``, ``eigener_text``, ``bezahlt_am`` und
            optional ``dokument_id``.
        positionen_liste: Die Positionen mit ``bezeichnung``, ``menge``,
            ``einheit``, ``preis`` und optional ``leistung_id``.

    Returns:
        Die Nummer des gespeicherten Dokuments.

    Die Nummer wird nicht auf Eindeutigkeit geprueft. Sie ist eine
    Projektnummer, und ein Projekt hat ein Angebot und eine Rechnung — beide
    tragen dieselbe.
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
        str(kopf.get("bezahlt_am", "")),
    )

    if dokument_id is None:
        cursor = db.execute(
            "INSERT INTO dokumente"
            " (art, nummer, kunde_id, datum, gueltig_bis, faellig, notiz,"
            "  eigener_text, bezahlt_am)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            werte,
        )
        neu = cursor.lastrowid or 0
    else:
        zuweisung = (
            "art = ?, nummer = ?, kunde_id = ?, datum = ?, gueltig_bis = ?,"
            " faellig = ?, notiz = ?, eigener_text = ?, bezahlt_am = ?"
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

    Die Nummer des Angebots wandert mit: Die Rechnung gehört zum selben
    Projekt und traegt dieselbe Nummer. Datum und Faelligkeit bleiben leer,
    weil die Rechnung ihr eigenes Datum bekommt.

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

    # Die Nummer wandert mit. Sie ist die Projektnummer, und das Angebot
    # und die Rechnung sind derselbe Vorgang: Aus Angebot 0199 wird Rechnung
    # 0199. Bis 0.8.2 stand hier ein leeres Feld, und es wurde die naechste
    # freie vorgeschlagen — aus einem Projekt wurden dadurch zwei.
    kopf: dict[str, str | int | None] = {
        "art": "rechnung",
        "nummer": dokument["nummer"],
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


# -------------------------------------------------------------- Stilllegen


def _aktiv_setzen(
    db: sqlite3.Connection, tabelle: str, kennung: int, aktiv: bool
) -> None:
    """Schaltet einen Datensatz auf aktiv oder stillgelegt.

    **Stilllegen ist nicht Löschen.** Ein Kunde mit fünf Rechnungen und eine
    Leistung, die auf alten Belegen noch auftaucht, dürfen nicht einfach
    verschwinden — die Belege würden mit verschwinden. Der Satz bleibt,
    er taucht nur in keiner Liste mehr auf.

    Bis hierher gab es die Spalte ``aktiv`` in der Datenbank, aber keinen
    Weg, sie zu setzen. Genau daran lag es, dass niemand sie benutzt hat.

    Args:
        db: Die Datenbankverbindung.
        tabelle: ``kunden`` oder ``leistungen``.
        kennung: Die Nummer des Datensatzes.
        aktiv: Ob er in den Listen stehen soll.

    Raises:
        ValueError: Wenn die Tabelle nicht eine der beiden ist.
    """
    if tabelle not in ("kunden", "leistungen"):
        raise ValueError(f"Unbekannte Tabelle: {tabelle}")

    db.execute(
        f"UPDATE {tabelle} SET aktiv = ? WHERE id = ?",  # noqa: S608
        (1 if aktiv else 0, kennung),
    )
    db.commit()


def kunde_stilllegen(
    db: sqlite3.Connection, kunde_id: int, aktiv: bool = False
) -> None:
    """Legt einen Kunden still oder holt ihn zurück.

    Args:
        db: Die Datenbankverbindung.
        kunde_id: Die Nummer des Kunden.
        aktiv: ``False`` legt still, ``True`` holt zurück.
    """
    _aktiv_setzen(db, "kunden", kunde_id, aktiv)


def leistung_stilllegen(
    db: sqlite3.Connection, leistung_id: int, aktiv: bool = False
) -> None:
    """Legt eine Leistung still oder holt sie zurück.

    Args:
        db: Die Datenbankverbindung.
        leistung_id: Die Nummer der Leistung.
        aktiv: ``False`` legt still, ``True`` holt zurück.
    """
    _aktiv_setzen(db, "leistungen", leistung_id, aktiv)


def kundenzahl(db: sqlite3.Connection, kunde_id: int) -> int:
    """Zählt, wie viele Dokumente an einem Kunden hängen.

    Für die Frage vor dem Löschen. Ein Kunde ohne Belege kann weg, einer
    mit fünf nicht — und das kann man nur wissen, wenn man nachzählt.

    Args:
        db: Die Datenbankverbindung.
        kunde_id: Die Nummer des Kunden.

    Returns:
        Die Zahl seiner Angebote und Rechnungen zusammen.
    """
    zeile = db.execute(
        "SELECT COUNT(*) FROM dokumente WHERE kunde_id = ?", (kunde_id,)
    ).fetchone()
    return int(zeile[0]) if zeile else 0


# ------------------------------------------------------------------ Projekte


def projekte(db: sqlite3.Connection) -> list[sqlite3.Row]:
    """Fasst die Dokumente zu Projekten zusammen.

    **Ein Projekt ist ein Kunde und eine Nummer.** Angebot 0199 und
    Rechnung 0199 sind ein Vorgang, nicht zwei. Die Projektnummer wird
    deshalb nicht mehr geprueft und nicht mehr zur Eindeutigkeit
    herangezogen — sie ist ein Name, den der Benutzer gibt.

    Aus den Dokumenten werden drei Zahlen, und die meinen nicht alle
    dasselbe:

    - ``summe`` ist das, was **berechnet** wurde. Gibt es keine Rechnung,
      steht dort das Angebot — denn das Angebot ist die Absicht, und die
      Rechnung die Tatsache.
    - ``offen`` ist der Betrag, auf den noch Geld fehlt. Nur Rechnungen
      zählen hinein; ein Angebot schuldet niemandem etwas.
    - ``angebote`` und ``rechnungen`` zaehlen, damit man sieht, ob ein
      Projekt schon abgerechnet ist oder noch nur angeboten wurde.

    Args:
        db: Die Datenbankverbindung.

    Returns:
        Die Projekte, die juengsten zuerst.
    """
    return list(
        db.execute(
            """
            SELECT
                d.kunde_id,
                COALESCE(k.firma, '(kein Kunde)') AS firma,
                d.nummer,
                MIN(d.datum) AS datum,
                SUM(CASE WHEN d.art = 'angebot' THEN 1 ELSE 0 END) AS angebote,
                SUM(CASE WHEN d.art = 'rechnung' THEN 1 ELSE 0 END) AS rechnungen,
                COALESCE(
                    SUM(
                        CASE WHEN d.art = 'rechnung' THEN 1 ELSE 0 END *
                        (SELECT COALESCE(SUM(p.menge * p.preis), 0)
                         FROM positionen AS p WHERE p.dokument_id = d.id)
                    ),
                    0
                ) AS rechnung_summe,
                COALESCE(
                    SUM(
                        CASE WHEN d.art = 'angebot' THEN 1 ELSE 0 END *
                        (SELECT COALESCE(SUM(p.menge * p.preis), 0)
                         FROM positionen AS p WHERE p.dokument_id = d.id)
                    ),
                    0
                ) AS angebot_summe,
                COALESCE(
                    SUM(
                        CASE WHEN d.art = 'rechnung' AND d.bezahlt_am = ''
                             THEN 1 ELSE 0 END *
                        (SELECT COALESCE(SUM(p.menge * p.preis), 0)
                         FROM positionen AS p WHERE p.dokument_id = d.id)
                    ),
                    0
                ) AS offen,
                MAX(CASE WHEN d.art = 'rechnung' THEN d.bezahlt_am ELSE '' END)
                    AS bezahlt_am,
                MIN(CASE WHEN d.art = 'rechnung' AND d.faellig != ''
                         THEN d.faellig ELSE '' END) AS faellig,
                MIN(CASE WHEN d.art = 'angebot' THEN d.gueltig_bis ELSE '' END)
                    AS gueltig_bis
            FROM dokumente AS d
            LEFT JOIN kunden AS k ON k.id = d.kunde_id
            GROUP BY d.kunde_id, d.nummer
            ORDER BY MIN(d.datum) DESC, MIN(d.id) DESC
            """
        )
    )


def projektsumme(projekt: sqlite3.Row) -> float:
    """Sagt, was ein Projekt bisher wert ist.

    **Die Rechnung schlaegt das Angebot.** Sonst stuende nach dem
    Abrechnen plötzlich eine andere Zahl in der Liste als vorher, ohne
    dass sich am Projekt etwas geaendert haette — nur weil ein zweites
    Dokument dazugekommen ist.

    Args:
        projekt: Eine Zeile aus :func:`projekte`.

    Returns:
        Die Rechnungssumme, oder — wo noch keine ist — die des Angebots.
    """
    rechnungen = float(projekt["rechnungen"] or 0)
    if rechnungen:
        return float(projekt["rechnung_summe"] or 0)
    return float(projekt["angebot_summe"] or 0)


def projektstand(projekt: sqlite3.Row) -> str:
    """Sagt, wo ein Projekt steht.

    Args:
        projekt: Eine Zeile aus :func:`projekte`.

    Returns:
        Ein Wort für die Liste.
    """
    if float(projekt["rechnungen"] or 0):
        if float(projekt["offen"] or 0) <= 0:
            return "bezahlt"
        if _ist_ueberfaellig(str(projekt["faellig"] or "")):
            return "überfällig"
        return "offen"
    if _ist_ueberfaellig(str(projekt["gueltig_bis"] or "")):
        return "abgelaufen"
    return "angeboten"


def _ist_ueberfaellig(frist: str) -> bool:
    """Sagt, ob eine Frist abgelaufen ist.

    **Datumswörter lassen sich nicht als Text vergleichen.** Gespeichert
    wird als ``TT.MM.JJJJ``, und in dieser Schreibweise stimmt sich
    Zeichen für Zeichen nur innerhalb desselben Jahres: „05.11.2026" ist
    Text *kleiner* als „15.10.2026", weil 0 kleiner ist als 1 — der
    5. November liegt aber drei Wochen in der Zukunft. Genau so stand eine
    fristlose Rechnung als *überfällig* in der Liste.

    Darum wird das Datum erst gelesen und dann verglichen, genau wie
    :func:`faktur.offen.ist_faellig` es tut. Was nicht lesbar ist, gilt
    nicht als abgelaufen.

    Args:
        frist: Das Datum aus der Datenbank.

    Returns:
        ``True``, wenn der Tag vor heute liegt.
    """
    if not frist:
        return False
    gefunden = betraege.lies_datum(frist)
    heute = betraege.lies_datum(betraege.heute())
    if gefunden is None or heute is None:
        return False
    return gefunden < heute


def projekt_belege(db: sqlite3.Connection, projekt: sqlite3.Row) -> list[sqlite3.Row]:
    """Gibt die Belege eines Projekts zurück, älteste zuerst.

    Args:
        db: Die Datenbankverbindung.
        projekt: Eine Zeile aus :func:`projekte`.

    Returns:
        Die Dokumente dieses Projekts. Das Angebot kommt vor der
        Rechnung, weil es das zeitlich frühere ist.
    """
    kunde_id = projekt["kunde_id"]
    if kunde_id is None:
        # Ohne Kunde gibt es nichts, wonach man suchen koennte.
        return []
    return list(
        db.execute(
            """
            SELECT d.*, COALESCE(k.firma, '(kein Kunde)') AS firma
            FROM dokumente AS d
            LEFT JOIN kunden AS k ON k.id = d.kunde_id
            WHERE d.kunde_id = ? AND d.nummer = ?
            ORDER BY d.datum, d.id
            """,
            (kunde_id, projekt["nummer"]),
        )
    )


# ------------------------------------------------------------- Auswertung


def _rechnungssummen(db: sqlite3.Connection) -> list[tuple[datetime.date, float]]:
    """Gibt zu jeder Rechnung ihr Datum und ihre Summe zurück.

    **Gelesen, nicht geschnitten.** Auf der Platte steht das Datum als
    ``TT.MM.JJJJ``, aber nicht nur: Bilder und ältere Fassungen haben
    ISO-Daten hineingeschrieben. Ein ``substr(datum, 1, 7)`` im SQL
    zählt beides falsch — und zählt es *unterschiedlich* falsch, was
    noch schlimmer ist. Hier wird jedes Datum einmal gelesen.

    Args:
        db: Die Datenbankverbindung.

    Returns:
        Je Rechnung das Datum und die Summe. Ohne Positionen steht eine
        Rechnung mit 0,00 € drin — sie ist ja da.
    """
    gefunden: list[tuple[datetime.date, float]] = []

    for zeile in db.execute(
        """
        SELECT d.datum AS datum,
               COALESCE(SUM(p.menge * p.preis), 0) AS summe
        FROM dokumente AS d
        LEFT JOIN positionen AS p ON p.dokument_id = d.id
        WHERE d.art = 'rechnung'
        GROUP BY d.id
        """
    ):
        gelesen = betraege.lies_datum(zeile["datum"])
        if gelesen is None:
            continue
        gefunden.append((gelesen, float(zeile["summe"])))

    return gefunden


class Monatssumme(NamedTuple):
    """Ein Monat auf der Uebersicht.

    Attributes:
        monat: Die Beschriftung, etwa ``10.26``.
        anzahl: Wie viele Rechnungen in dem Monat ausgestellt wurden.
        summe: Ihre Summe zusammen.
    """

    monat: str
    anzahl: int
    summe: float


def monatssummen(db: sqlite3.Connection, anzahl: int = 12) -> list[Monatssumme]:
    """Rechnet die Rechnungssummen je Monat aus, die letzten ``anzahl``.

    **Nach dem Rechnungsdatum, nicht dem Zahlungsdatum.** Gefragt ist,
    was in einem Monat in Rechnung gestellt wurde. Wer wissen will, was
    auch wirklich hereingekommen ist, findet das auf der Seite *Offene
    Forderungen* — dort steht jede Rechnung mit ihrem Zahlungsdatum.

    Args:
        db: Die Datenbankverbindung.
        anzahl: Wie viele Monate zurück. 12 sind ein Jahr.

    Returns:
        Je Monat eine Beschriftung, die Zahl der Rechnungen und die
        Summe. Der älteste zuerst, damit man von links nach rechts liest.
    """
    heute = betraege.lies_datum(betraege.heute())
    if heute is None:
        return []

    # Die gewollten Monate als (Jahr, Monat), der älteste zuerst.
    erster = heute.year * 12 + heute.month - 1 - (anzahl - 1)
    monate = [
        (gesamt // 12, gesamt % 12 + 1) for gesamt in range(erster, erster + anzahl)
    ]

    summen: dict[tuple[int, int], float] = dict.fromkeys(monate, 0.0)
    gezahlt: dict[tuple[int, int], int] = dict.fromkeys(monate, 0)
    for tag, summe in _rechnungssummen(db):
        if (tag.year, tag.month) in summen:
            summen[(tag.year, tag.month)] += summe
            gezahlt[(tag.year, tag.month)] += 1

    return [
        Monatssumme(
            f"{monat:02d}.{str(jahr)[2:]}",
            gezahlt[(jahr, monat)],
            summen[(jahr, monat)],
        )
        for jahr, monat in monate
    ]


def jahreszahlen(db: sqlite3.Connection, jahr: int | None = None) -> tuple[int, float]:
    """Sagt, was dieses Jahr in Rechnung gestellt wurde.

    **Zahl und Summe zusammen.** Beide stehen auf der Übersicht unter
    derselben Zahl, und sie kommen aus derselben Rechnung. Zwei
    Funktionen — eine fuer die Zahl, eine fuer die Summe — wuerden zwei
    Stellen sein, an denen die Jahre auseinanderlaufen koennen.

    Args:
        db: Die Datenbankverbindung.
        jahr: Das Jahr. Ohne Angabe das laufende.

    Returns:
        Wie viele Rechnungen es waren und was sie zusammen machen.
        Bezahlt oder nicht — gezahlt wird nicht verbucht, sondern
        abgebucht, und das steht bei den offenen Forderungen.
    """
    heute = betraege.lies_datum(betraege.heute())
    gesucht = jahr if jahr is not None else (heute.year if heute else 0)

    zeilen = [
        (tag, summe) for tag, summe in _rechnungssummen(db) if tag.year == gesucht
    ]
    return len(zeilen), sum(summe for _tag, summe in zeilen)


def offene_angebote(db: sqlite3.Connection) -> list[sqlite3.Row]:
    """Gibt die Projekte zurück, die noch nicht abgerechnet sind.

    **Ein Angebot ist kein Geld.** Es steht hier, weil man wissen will,
    was dem Kunden angeboten wurde und noch keine Rechnung daraus kam —
    nicht, weil es eine Forderung wäre. Das ist der Unterschied zu
    :func:`faktur.offen.offene`, und die beiden werden leicht
    verwechselt.

    Args:
        db: Die Datenbankverbindung.

    Returns:
        Die Projekte ohne Rechnung.
    """
    return [p for p in projekte(db) if not float(p["rechnungen"] or 0)]
