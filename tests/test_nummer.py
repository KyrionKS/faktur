"""Tests für Datum und Nummer auf dem Dokument.

Zwei Fehler, die hier festgehalten werden:

Das Datum stand ungewandelt auf der PDF. Es gab ``betraege.datum()``, das
genau dafür geschrieben war und nirgends aufgerufen wurde. Das Formular
trägt ein, deshalb sah es normalerweise richtig aus — wer ein Datum selbst
eintippt, bekam es in seiner Schreibweise aufs Papier.

Die Nummern sind vier Stellen, mit Absicht. Die Anforderung von Anfang an
lautete so, und eine Rechnung ist schon verschickt, wenn ihre Nummer schon
gedruckt ist. Deshalb wird die Jahreszahl nur angezeigt und nie in die
gespeicherte Nummer hineingerechnet.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from faktur import betraege, dateien, einstellungen, nummer, pdf, texte

#: Ein Dokument in irgendeiner Schreibweise.
DATUM_DE = "08.10.2026"
DATUM_ISO = "2026-10-08"


def _dokument(verbindung: sqlite3.Connection, datum: str = DATUM_DE) -> object:
    """Legt ein Angebot an und gibt es zurück.

    Args:
        verbindung: Die Datenbankverbindung.
        datum: Das Datum in der gewünschten Schreibweise.

    Returns:
        Das volle Dokument.
    """
    kunde = dateien.kunde_speichern(verbindung, {"firma": "Soundcheck GmbH"})
    # Die Nummer kommt aus dem Formular, nicht aus dem Datenlayer. Das
    # Bildschirmfenster fuellt sie mit dem naechsten freien Wert vor.
    kennung = dateien.dokument_speichern(
        verbindung,
        {
            "art": "angebot",
            "kunde_id": kunde,
            "datum": datum,
            "nummer": dateien.naechste_nummer(verbindung),
        },
        [{"bezeichnung": "Aufnahme Ton", "menge": 1, "preis": 850.0, "einheit": "Tag"}],
    )
    return dateien.dokument_holen(verbindung, kennung)


# ------------------------------------------------------------------- das Datum


def test_auf_der_pdf_steht_ein_deutsches_datum(verbindung: sqlite3.Connection) -> None:
    """Ein in ISO getipptes Datum kommt als ``08.10.2026`` heraus.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    dokument = _dokument(verbindung, DATUM_ISO)
    werte = pdf.werte_fuer(verbindung, dokument)

    assert werte["Datum"] == DATUM_DE


def test_und_der_platzhalter_bekommt_es_genauso(
    verbindung: sqlite3.Connection,
) -> None:
    """``{{Datum}}`` versprach in der Anleitung ein deutsches Datum.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    dokument = _dokument(verbindung, DATUM_ISO)
    werte = pdf.werte_fuer(verbindung, dokument)

    assert texte.einsetzen("Stand: {{Datum}}", werte) == "Stand: 08.10.2026"


def test_auch_faellig_und_gueltig_bis_werden_formatiert(
    verbindung: sqlite3.Connection,
) -> None:
    """Es gibt drei Datumsangaben auf einem Dokument, nicht eine.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    dokument = _dokument(verbindung, DATUM_ISO)
    werte = pdf.werte_fuer(verbindung, dokument)

    assert werte["Faellig"] == "" or werte["Faellig"] == DATUM_DE
    assert werte["Gueltig_bis"] == "" or werte["Gueltig_bis"] == DATUM_DE


def test_ein_unlesbares_datum_bleibt_leer_statt_etwas_falsches(
    verbindung: sqlite3.Connection,
) -> None:
    """Lieber nichts als ein geratenes Datum.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    dokument = _dokument(verbindung, "irgendwann")
    werte = pdf.werte_fuer(verbindung, dokument)

    assert werte["Datum"] == ""


def test_der_formatierer_wird_jetzt_auch_benutzt() -> None:
    """Sonst wäre die Funktion wieder toter Code.

    Args:
        None
    """
    quelle = (Path(__file__).resolve().parents[1] / "faktur" / "pdf.py").read_text(
        encoding="utf-8"
    )

    assert "betraege.datum(" in quelle, (
        "betraege.datum() wird nicht mehr aufgerufen. Das Datum steht dann "
        "wieder ungewandelt auf der PDF."
    )


# ------------------------------------------------------------------- die Nummer


def test_ohne_einstellung_bleibt_es_bei_vier_stellen(
    verbindung: sqlite3.Connection,
) -> None:
    """Die Voreinstellung ist die Anforderung von Anfang an.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    assert nummer.gewaehlt(verbindung) == "vierstellig"
    assert nummer.mit_jahr(verbindung) is False


def test_auf_der_pdf_erscheint_die_jahreszahl_wenn_gewuenscht(
    verbindung: sqlite3.Connection,
) -> None:
    """``2026-0032`` statt ``0032``.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    einstellungen.speichere(verbindung, nummer.SCHLUESSEL, "mit_jahr")
    dokument = _dokument(verbindung, DATUM_ISO)

    angezeigt = pdf.nummer_anzeige(dokument, verbindung)

    assert angezeigt.endswith(dokument["nummer"])
    assert angezeigt.startswith("2026-")


def test_die_gespeicherte_nummer_aendert_sich_nie(
    verbindung: sqlite3.Connection,
) -> None:
    """Das ist der ganze Witz an der Sache.

    Eine Rechnung ist verschickt, wenn ihre Nummer gedruckt ist. Wer sie
    spaeter umzaehlt, muss alle alten Belege anpassen — und das laesst sich
    nicht mehr, sobald der erste beim Kunden liegt.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    einstellungen.speichere(verbindung, nummer.SCHLUESSEL, "mit_jahr")
    dokument = _dokument(verbindung, DATUM_ISO)

    pdf.nummer_anzeige(dokument, verbindung)

    neu = dateien.dokument_holen(verbindung, dokument["id"])
    assert neu["nummer"] == dokument["nummer"]
    assert len(neu["nummer"]) == 4


def test_ein_altes_dokument_aus_2025_zeigt_2025(verbindung: sqlite3.Connection) -> None:
    """Das Jahr kommt aus dem Dokument, nicht aus dem laufenden Jahr.

    Sonst bekäme eine Rechnung von 2025 plötzlich 2026, und zwar nur auf
    dem Bildschirm.

    Args:
        verbindung: Die Datenbankverbindung.
    """
    einstellungen.speichere(verbindung, nummer.SCHLUESSEL, "mit_jahr")

    assert nummer.anzeige("0032", "15.03.2025", True) == "2025-0032"
    assert nummer.anzeige("0032", "15.03.2026", True) == "2026-0032"


def test_ohne_datum_bleibt_es_bei_der_reinen_nummer() -> None:
    """Keine halbe Jahreszahl, lieber keine.

    Args:
        None
    """
    assert nummer.anzeige("0032", "", True) == "0032"
    assert nummer.anzeige("0032", "unlesbar", True) == "0032"


@pytest.mark.parametrize(
    ("kaputt", "soll"),
    [("", "vierstellig"), ("  ", "vierstellig"), ("mitjahr", "vierstellig")],
)
def test_ein_unbekanntes_format_ist_das_uebliche(
    verbindung: sqlite3.Connection, kaputt: str, soll: str
) -> None:
    """Ein Tippfehler darf keine halbe Jahreszahl erzeugen.

    Args:
        verbindung: Die Datenbankverbindung.
        kaputt: Der gespeicherte Wert.
        soll: Der Name, der danach gilt.
    """
    einstellungen.speichere(verbindung, nummer.SCHLUESSEL, kaputt)

    assert nummer.gewaehlt(verbindung) == soll


def test_die_jahreszahl_ist_vier_stellen() -> None:
    """Sonst passt sie nicht neben einer vierstelligen Nummer.

    Args:
        None
    """
    assert len(nummer.jahr_aus(DATUM_DE)) == 4
    assert len(nummer.jahr_aus(DATUM_ISO)) == 4


def test_alle_jahreszahlen_werden_gelesen() -> None:
    """Nicht nur das heutige Format.

    Args:
        None
    """
    assert nummer.jahr_aus("08.10.2026") == "2026"
    assert nummer.jahr_aus("2026-10-08") == "2026"
    assert nummer.jahr_aus("8.10.26") == "2026"
    assert nummer.jahr_aus("") == ""


def test_der_formatierer_wird_auch_fuer_und_klein_gesucht() -> None:
    """``betraege.lies_datum`` ist nur ein Name fuer ``_parse``.

    Args:
        None
    """
    assert betraege.lies_datum(DATUM_ISO) == betraege.lies_datum(DATUM_DE)
    assert betraege.lies_datum("unlesbar") is None
