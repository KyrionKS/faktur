"""Tests für die offenen Forderungen.

Das Wichtigste hier ist der Test, dass ein Angebot nicht bezahlt sein kann.
Es wird ja gar nicht in Rechnung gestellt. Ein als bezahlt markiertes
Angebot wäre eine Angabe, die nicht stimmt, und die stünde danach einfach da,
ohne dass jemand sie anzweifelt.

Die Voreinstellung ist außerdem, dass eine bestehende Rechnung *offen* ist.
Eine Rechnung, die schon beim Kunden liegt, gilt nicht als bezahlt, weil sie
bezahlt ist — das weiß niemand. Sonst verschwindet sie beim ersten Öffnen
des Programms aus der Liste der offenen Posten.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from faktur import dateien, db, offen

#: Der Stichtag — **in der Schreibweise, die das Programm wirklich
#: benutzt.**
#:
#: Vorher stand hier ``"2026-10-08"``, also in ISO. Damit passte der Test
#: zu ``ist_faellig``, das innen ``isoformat()`` erzeugt — aber der einzige
#: Aufrufer im Programm übergibt :func:`faktur.betraege.heute`, und die
#: liefert ``TT.MM.JJJJ``. Der Test prüfte also eine Schreibweise, die im
#: Betrieb nicht vorkommt, und die Seite *Offene Forderungen* zeigte
#: darum so gut wie nie *überfällig*.
HEUTE = "08.10.2026"


def rechnung_anlegen(
    verbindung: sqlite3.Connection,
    nummer: str = "0001",
    faellig: str = "",
    bezahlt: str = "",
    preis: float = 850.0,
) -> int:
    """Legt eine Rechnung an und gibt ihre Kennung zurück.

    Args:
        verbindung: Die Datenbankverbindung.
        nummer: Die Nummer der Rechnung.
        faellig: Das Fälligkeitsdatum.
        bezahlt: Das Zahlungsdatum, leer für offen.
        preis: Der Betrag der einen Position.

    Returns:
        Die Kennung des Dokuments.
    """
    kunde = dateien.kunde_speichern(verbindung, {"firma": "Soundcheck GmbH"})
    kopf = {
        "art": "rechnung",
        "nummer": nummer,
        "kunde_id": kunde,
        "datum": "01.10.2026",
        "faellig": faellig,
        "bezahlt_am": bezahlt,
    }
    return dateien.dokument_speichern(
        verbindung,
        kopf,
        [{"bezeichnung": "Aufnahme", "menge": 1, "preis": preis, "einheit": "Tag"}],
    )


def angebot_anlegen(verbindung: sqlite3.Connection, nummer: str = "0001") -> int:
    """Legt ein Angebot an und gibt seine Kennung zurück.

    Args:
        verbindung: Die Datenbankverbindung.
        nummer: Die Nummer des Angebots.

    Returns:
        Die Kennung des Dokuments.
    """
    kunde = dateien.kunde_speichern(verbindung, {"firma": "Soundcheck GmbH"})
    return dateien.dokument_speichern(
        verbindung,
        {"art": "angebot", "nummer": nummer, "kunde_id": kunde, "datum": "01.10.2026"},
        [{"bezeichnung": "Aufnahme", "menge": 1, "preis": 850.0, "einheit": "Tag"}],
    )


def auf_alten_stand_bringen(verbindung: sqlite3.Connection) -> None:
    """Nimmt einer frischen Datenbank die neue Spalte wieder weg.

    Damit laeuft die Migration im naechsten Schritt wirklich, statt an
    einer Spalte vorbeizulaufen, die schon da ist.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    verbindung.execute("ALTER TABLE dokumente DROP COLUMN bezahlt_am")
    verbindung.execute(
        "UPDATE einstellungen SET wert = '2' WHERE schluessel = ?",
        (db.SCHLUESSEL_STUFE,),
    )
    verbindung.commit()


# --------------------------------------------------------------- die Frage


def test_eine_neue_rechnung_ist_offen(verbindung: sqlite3.Connection) -> None:
    """Eine Rechnung gilt als offen, bis jemand etwas einträgt.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    kennung = rechnung_anlegen(verbindung)

    assert offen.ist_offen(dateien.dokument_holen(verbindung, kennung)) is True


def test_ein_angebot_ist_nie_offen(verbindung: sqlite3.Connection) -> None:
    """Auf ein Angebot wartet niemand auf Geld.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    kennung = angebot_anlegen(verbindung)

    assert offen.ist_offen(dateien.dokument_holen(verbindung, kennung)) is False


def test_eine_bezahlte_rechnung_ist_nicht_offen(verbindung: sqlite3.Connection) -> None:
    """Args:
    verbindung: Die Datenbankverbindung.
    """
    kennung = rechnung_anlegen(verbindung, bezahlt="05.10.2026")
    dokument = dateien.dokument_holen(verbindung, kennung)

    assert offen.ist_offen(dokument) is False
    assert offen.ist_bezahlt(dokument) is True


# --------------------------------------------------------------- die Liste


def test_die_liste_zeigt_nur_offene_rechnungen(
    verbindung: sqlite3.Connection,
) -> None:
    """Weder Angebote noch bezahlte Rechnungen.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    offen_nr = rechnung_anlegen(verbindung, "0001")
    rechnung_anlegen(verbindung, "0002", bezahlt="05.10.2026")
    angebot_anlegen(verbindung, "0003")

    gefunden = offen.offene(verbindung)

    assert [d["id"] for d in gefunden] == [offen_nr]


def test_die_liste_ist_nach_frist_sortiert(verbindung: sqlite3.Connection) -> None:
    """Die älteste zuerst, weil sie am dringendsten ist.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    spaet = rechnung_anlegen(verbindung, "0001", faellig="30.09.2026")
    frueh = rechnung_anlegen(verbindung, "0002", faellig="01.09.2026")

    gefunden = offen.offene(verbindung)

    assert [d["id"] for d in gefunden] == [frueh, spaet]


def test_die_summe_zaehlt_nur_die_offenen(verbindung: sqlite3.Connection) -> None:
    """Eine bezahlte Rechnung gehört nicht in die Summe.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    rechnung_anlegen(verbindung, "0001", preis=850.0)
    rechnung_anlegen(verbindung, "0002", preis=1200.0, bezahlt="05.10.2026")

    assert offen.summe_offen(verbindung) == pytest.approx(850.0)


def test_ohne_rechnungen_ist_die_summe_null(verbindung: sqlite3.Connection) -> None:
    """Null, nicht ein Fehler.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    angebot_anlegen(verbindung)

    assert offen.summe_offen(verbindung) == 0.0


# --------------------------------------------------------------- ueberfaellig


def test_eine_offene_rechnung_kann_ueberfaellig_sein(
    verbindung: sqlite3.Connection,
) -> None:
    """Args:
    verbindung: Die Datenbankverbindung.
    """
    kennung = rechnung_anlegen(verbindung, faellig="01.10.2026")

    assert offen.ist_faellig(dateien.dokument_holen(verbindung, kennung), HEUTE) is True


def test_eine_noch_nicht_faellige_rechnung_ist_es_nicht(
    verbindung: sqlite3.Connection,
) -> None:
    """Args:
    verbindung: Die Datenbankverbindung.
    """
    kennung = rechnung_anlegen(verbindung, faellig="30.11.2026")

    assert (
        offen.ist_faellig(dateien.dokument_holen(verbindung, kennung), HEUTE) is False
    )


def test_eine_bezahlte_rechnung_ist_nie_ueberfaellig(
    verbindung: sqlite3.Connection,
) -> None:
    """Vergessen zu bezahlen und fristgerecht bezahlt sehen gleich aus.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    kennung = rechnung_anlegen(verbindung, faellig="01.10.2026", bezahlt="02.10.2026")

    assert (
        offen.ist_faellig(dateien.dokument_holen(verbindung, kennung), HEUTE) is False
    )


@pytest.mark.parametrize("frist", ["01.10.2026", "2026-10-01", "1.10.26"])
def test_die_frist_gilt_in_jeder_schreibweise(
    verbindung: sqlite3.Connection, frist: str
) -> None:
    """Sonst hing die Antwort davon ab, wie jemand das Datum getippt hat.

    Args:
        verbindung: Die Datenbankverbindung.
        frist: Das Fälligkeitsdatum in irgendeiner Schreibweise.
    """
    kennung = rechnung_anlegen(verbindung, faellig=frist)

    assert offen.ist_faellig(dateien.dokument_holen(verbindung, kennung), HEUTE) is True


def test_ohne_frist_ist_nichts_ueberfaellig(verbindung: sqlite3.Connection) -> None:
    """Ohne Frist gibt es nichts, was abgelaufen sein könnte.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    kennung = rechnung_anlegen(verbindung)

    assert (
        offen.ist_faellig(dateien.dokument_holen(verbindung, kennung), HEUTE) is False
    )


def test_ein_unlesbares_datum_zaehlt_nicht_als_ueberfaellig(
    verbindung: sqlite3.Connection,
) -> None:
    """Lieber nicht, als jemanden zu Unrecht anzuschreiben.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    kennung = rechnung_anlegen(verbindung, faellig="irgendwann")

    assert (
        offen.ist_faellig(dateien.dokument_holen(verbindung, kennung), HEUTE) is False
    )


# --------------------------------------------------------------- markieren


def test_eine_rechnung_laesst_sich_als_bezahlt_markieren(
    verbindung: sqlite3.Connection,
) -> None:
    """Args:
    verbindung: Die Datenbankverbindung.
    """
    kennung = rechnung_anlegen(verbindung)

    assert offen.als_bezahlt_markieren(verbindung, kennung, "05.10.2026") is True

    neu = dateien.dokument_holen(verbindung, kennung)
    assert neu["bezahlt_am"] == "05.10.2026"


def test_und_wieder_als_offen(verbindung: sqlite3.Connection) -> None:
    """Ein Irrtum muss sich zurücknehmen lassen.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    kennung = rechnung_anlegen(verbindung, bezahlt="05.10.2026")

    offen.als_bezahlt_markieren(verbindung, kennung, "")

    neu = dateien.dokument_holen(verbindung, kennung)
    assert neu["bezahlt_am"] == ""
    assert offen.ist_offen(neu) is True


def test_ein_angebot_laesst_sich_nicht_als_bezahlt_markieren(
    verbindung: sqlite3.Connection,
) -> None:
    """Das ist die wichtigste Regel in dieser Datei.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    kennung = angebot_anlegen(verbindung)

    ergebnis = offen.als_bezahlt_markieren(verbindung, kennung, "05.10.2026")

    assert ergebnis is False
    assert dateien.dokument_holen(verbindung, kennung)["bezahlt_am"] == ""


def test_ein_gibts_nicht_aendert_auch_nichts(verbindung: sqlite3.Connection) -> None:
    """Args:
    verbindung: Die Datenbankverbindung.
    """
    assert offen.als_bezahlt_markieren(verbindung, 9999, "05.10.2026") is False


# --------------------------------------------------------------- die Migration


def test_eine_neue_datenbank_hat_die_spalte(verbindung: sqlite3.Connection) -> None:
    """Args:
    verbindung: Die Datenbankverbindung.
    """
    spalten = [
        zeile["name"] for zeile in verbindung.execute("PRAGMA table_info(dokumente)")
    ]

    assert "bezahlt_am" in spalten
    assert db.SCHEMA_STUFE >= 3


def test_die_spalte_kommt_hinter_alle_vorhandenen(
    verbindung: sqlite3.Connection,
) -> None:
    """Sonst ginge beim Ergänzen eine Spalte verloren.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    auf_alten_stand_bringen(verbindung)

    db._wandern(verbindung, Path("egal"))  # type: ignore[arg-type]

    spalten = [
        zeile["name"] for zeile in verbindung.execute("PRAGMA table_info(dokumente)")
    ]

    assert spalten[-1] == "bezahlt_am"


def test_eine_bestehende_rechnung_bleibt_offen(tmp_path: Path) -> None:
    """Eine Rechnung, die schon beim Kunden liegt, gilt nicht als bezahlt.

    Args:
        tmp_path: Das temporäre Verzeichnis.
    """
    datei = tmp_path / "alt.db"

    alt = db.verbinden(datei)
    kunde = dateien.kunde_speichern(alt, {"firma": "Soundcheck GmbH"})
    kennung = dateien.dokument_speichern(
        alt,
        {
            "art": "rechnung",
            "nummer": "0001",
            "kunde_id": kunde,
            "datum": "01.10.2026",
            "faellig": "15.10.2026",
        },
        [{"bezeichnung": "Aufnahme", "menge": 1, "preis": 850.0, "einheit": "Tag"}],
    )
    auf_alten_stand_bringen(alt)
    alt.close()

    neu = db.verbinden(datei)

    assert offen.ist_offen(dateien.dokument_holen(neu, kennung)) is True
    assert offen.summe_offen(neu) == pytest.approx(850.0)

    neu.close()


# ------------------------------------- Der Weg, den das Programm wirklich geht


def test_und_das_gilt_fuer_das_datum_wie_es_das_programm_bekommt(
    verbindung: sqlite3.Connection,
) -> None:
    """**Dieser Test ist der Grund fuer den ganzen Abschnitt.**

    :func:`faktur.offen.ist_faellig` vergleicht zwei Daten. In den Tests
    stand links ein Datum in ISO und rechts eines in deutscher
    Schreibweise — und damit war die Frist praktisch nie abgelaufen. Ein
    Beleg mit Frist seit dem 1. Januar 2020 wurde nicht als *überfällig*
    gemeldet, an einem 8. Oktober.

    Geprueft wird deshalb der Aufruf, wie er im Fenster steht:
    ``beträge.heute()``.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    from faktur import betraege

    kennung = rechnung_anlegen(verbindung, nummer="0001", faellig="01.01.2020")

    assert (
        offen.ist_faellig(dateien.dokument_holen(verbindung, kennung), betraege.heute())
        is True
    ), "Eine seit 2020 abgelaufene Rechnung wird nicht als überfällig gemeldet."


def test_und_und_umgekehrt(
    verbindung: sqlite3.Connection,
) -> None:
    """Eine Frist in der Zukunft ist nicht überfällig.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    from faktur import betraege

    kennung = rechnung_anlegen(verbindung, nummer="0002", faellig="31.12.2099")

    assert (
        offen.ist_faellig(dateien.dokument_holen(verbindung, kennung), betraege.heute())
        is False
    )


def test_und_die_ueberfaelligen_summieren_sich_richtig(
    verbindung: sqlite3.Connection,
) -> None:
    """Die überfälligen sind eine Teilmenge der offenen, nicht alle.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    alt = rechnung_anlegen(verbindung, nummer="0003", faellig="01.01.2020", preis="100")
    neu = rechnung_anlegen(verbindung, nummer="0004", faellig="31.12.2099", preis="250")
    del alt, neu

    alles = offen.summe_offen(verbindung)
    dringend = offen.summe_ueberfaellig(verbindung)

    assert dringend == 100.0, f"Ueberfaellig sind {dringend}, erwartet 100"
    assert dringend < alles, "Ueberfaellig und offen sind dieselbe Zahl"
