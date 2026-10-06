"""Tests für die Erzeugung der PDF."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from faktur import dateien, einstellungen, pdf


def _vorbereiten(db: sqlite3.Connection) -> int:
    """Legt Stammdaten und ein Dokument an.

    Args:
        db: Die Testdatenbank.

    Returns:
        Die Nummer des Dokuments.
    """
    for name, wert in (
        ("firma", "New Air Media Group"),
        ("zusatz", "Tonstudio & Medienproduktion"),
        ("strasse", "Soundweg 12"),
        ("plz", "10999"),
        ("ort", "Berlin"),
        ("email", "ton@newair.de"),
        ("bank", "Deutsche Kreditbank"),
        ("iban", "DE02 1203 0000 0000 2020 51"),
        ("bic", "BYLADEM1001"),
        ("steuernummer", "12/345/67890"),
        ("inhaber", "Kyrion"),
    ):
        einstellungen.speichere(db, name, wert)

    kunde_id = dateien.kunde_speichern(
        db,
        {
            "firma": "Soundcheck GmbH",
            "ansprechpartner": "Herr Max Mustermann",
            "strasse": "Klangstrasse 3",
            "plz": "10115",
            "ort": "Berlin",
        },
    )

    return dateien.dokument_speichern(
        db,
        {
            "art": "rechnung",
            "nummer": "2026-001",
            "kunde_id": kunde_id,
            "datum": "06.10.2026",
            "faellig": "20.10.2026",
        },
        [
            {
                "bezeichnung": "Aufnahme Ton",
                "menge": "2",
                "einheit": "Tag",
                "preis": "850",
            },
            {
                "bezeichnung": "Mischung und Mastering",
                "menge": "10",
                "einheit": "Stunde",
                "preis": "95",
            },
        ],
    )


def test_rechnung_wird_geschrieben(
    verbindung: sqlite3.Connection, tmp_path: Path
) -> None:
    """Legt eine echte Datei an.

    Args:
        verbindung: Die Testdatenbank.
        tmp_path: Das temporäre Verzeichnis von pytest.
    """
    dokument_id = _vorbereiten(verbindung)
    dokument = dateien.dokument_holen(verbindung, dokument_id)
    assert dokument is not None

    ziel = tmp_path / "rechnung.pdf"
    pdf.erzeugen(verbindung, dokument, ziel)

    assert ziel.is_file()
    assert ziel.stat().st_size > 1000
    assert ziel.read_bytes().startswith(b"%PDF")


def test_angebot_wird_geschrieben(
    verbindung: sqlite3.Connection, tmp_path: Path
) -> None:
    """Auch ein Angebot kommt als PDF heraus.

    Args:
        verbindung: Die Testdatenbank.
        tmp_path: Das temporäre Verzeichnis von pytest.
    """
    _vorbereiten(verbindung)
    kunde = dateien.kunden(verbindung)[0]
    dokument_id = dateien.dokument_speichern(
        verbindung,
        {
            "art": "angebot",
            "nummer": "ANG-2026-001",
            "kunde_id": kunde["id"],
            "datum": "06.10.2026",
            "gueltig_bis": "27.10.2026",
        },
        [{"bezeichnung": "Jingle", "menge": "1", "einheit": "Stück", "preis": "450"}],
    )

    dokument = dateien.dokument_holen(verbindung, dokument_id)
    assert dokument is not None

    ziel = tmp_path / "angebot.pdf"
    pdf.erzeugen(verbindung, dokument, ziel)

    assert ziel.is_file()
    assert ziel.read_bytes().startswith(b"%PDF")


def test_ohne_positionen_ist_das_kein_fehler(
    verbindung: sqlite3.Connection, tmp_path: Path
) -> None:
    """Ein leeres Dokument wird trotzdem geschrieben.

    Args:
        verbindung: Die Testdatenbank.
        tmp_path: Das temporäre Verzeichnis von pytest.
    """
    _vorbereiten(verbindung)
    dokument_id = dateien.dokument_speichern(
        verbindung, {"art": "rechnung", "nummer": "R-leer", "datum": "06.10.2026"}, []
    )

    dokument = dateien.dokument_holen(verbindung, dokument_id)
    assert dokument is not None

    ziel = tmp_path / "leer.pdf"
    pdf.erzeugen(verbindung, dokument, ziel)

    assert ziel.is_file()


def test_ohne_stammdaten_geht_es_trotzdem(
    verbindung: sqlite3.Connection, tmp_path: Path
) -> None:
    """Fehlende Stammdaten dürfen nichts stoppen.

    Args:
        verbindung: Die Testdatenbank.
        tmp_path: Das temporäre Verzeichnis von pytest.
    """
    dokument_id = dateien.dokument_speichern(
        verbindung,
        {"art": "rechnung", "nummer": "R-nackt", "datum": "06.10.2026"},
        [{"bezeichnung": "Ton", "menge": "1", "preis": "100"}],
    )

    dokument = dateien.dokument_holen(verbindung, dokument_id)
    assert dokument is not None

    ziel = tmp_path / "nackt.pdf"
    pdf.erzeugen(verbindung, dokument, ziel)

    assert ziel.is_file()


def test_sonderzeichen_in_der_bezeichnung(
    verbindung: sqlite3.Connection, tmp_path: Path
) -> None:
    """Zeichen wie ``&`` und ``<`` dürfen den Aufbau nicht sprengen.

    Args:
        verbindung: Die Testdatenbank.
        tmp_path: Das temporäre Verzeichnis von pytest.
    """
    _vorbereiten(verbindung)
    dokument_id = dateien.dokument_speichern(
        verbindung,
        {"art": "rechnung", "nummer": "R-xml", "datum": "06.10.2026"},
        [
            {"bezeichnung": "Mix & Master <Special>", "menge": "1", "preis": "500"},
            {"bezeichnung": 'Größe 5" – Live', "menge": "1", "preis": "100"},
        ],
    )

    dokument = dateien.dokument_holen(verbindung, dokument_id)
    assert dokument is not None

    ziel = tmp_path / "sonderzeichen.pdf"
    pdf.erzeugen(verbindung, dokument, ziel)

    assert ziel.is_file()


def test_sehr_langes_dokument_wird_mehrseitig(
    verbindung: sqlite3.Connection, tmp_path: Path
) -> None:
    """Viele Positionen ergeben mehr als eine Seite.

    Args:
        verbindung: Die Testdatenbank.
        tmp_path: Das temporäre Verzeichnis von pytest.
    """
    _vorbereiten(verbindung)
    positionen = [
        {
            "bezeichnung": f"Position Nummer {nummer} mit langem Text",
            "menge": "1",
            "einheit": "Stunde",
            "preis": "100",
        }
        for nummer in range(1, 80)
    ]
    dokument_id = dateien.dokument_speichern(
        verbindung,
        {"art": "rechnung", "nummer": "R-lang", "datum": "06.10.2026"},
        positionen,
    )

    dokument = dateien.dokument_holen(verbindung, dokument_id)
    assert dokument is not None

    ziel = tmp_path / "lang.pdf"
    pdf.erzeugen(verbindung, dokument, ziel)

    assert ziel.is_file()

    seiten = ziel.read_bytes().count(b"/Type /Page\n") + ziel.read_bytes().count(
        b"/Type /Page>"
    )
    assert seiten > 1


def test_werte_fuer_die_platzhalter(verbindung: sqlite3.Connection) -> None:
    """Sammelt die Werte für den Brieftext.

    Args:
        verbindung: Die Testdatenbank.
    """
    dokument_id = _vorbereiten(verbindung)
    dokument = dateien.dokument_holen(verbindung, dokument_id)
    assert dokument is not None

    werte = pdf.werte_fuer(verbindung, dokument)

    assert werte["Kunde"] == "Soundcheck GmbH"
    assert werte["Kunde_Anrede"] == "Herr Mustermann"
    assert werte["Ansprechpartner"] == "Herr Max Mustermann"
    assert werte["Nummer"] == "2026-001"
    assert werte["Betrag"] == "2.650,00 €"
    assert werte["Anzahl_Positionen"] == "2"
    assert werte["EigeneFirma"] == "New Air Media Group"


def test_dateiname_ist_fuer_dateisysteme_sicher(verbindung: sqlite3.Connection) -> None:
    """Ein Schrägstrich im Firmennamen darf keinen Ordner erzeugen.

    Args:
        verbindung: Die Testdatenbank.
    """
    from faktur.screens.dokumente import dateiname

    kunde_id = dateien.kunde_speichern(verbindung, {"firma": "Bild/Video AG"})
    dokument_id = dateien.dokument_speichern(
        verbindung,
        {
            "art": "rechnung",
            "nummer": "R/1",
            "kunde_id": kunde_id,
            "datum": "06.10.2026",
        },
        [],
    )

    dokument = dateien.dokument_holen(verbindung, dokument_id)
    assert dokument is not None

    name = dateiname(dokument, "rechnung")

    assert "/" not in name
    assert "Bild-Video AG" in name


@pytest.mark.parametrize("art", ["angebot", "rechnung"])
def test_beide_arten_gehen(
    verbindung: sqlite3.Connection, tmp_path: Path, art: str
) -> None:
    """Beide Dokumentarten kommen durch denselben Aufbau.

    Args:
        verbindung: Die Testdatenbank.
        tmp_path: Das temporäre Verzeichnis von pytest.
        art: ``angebot`` oder ``rechnung``.
    """
    _vorbereiten(verbindung)
    dokument_id = dateien.dokument_speichern(
        verbindung,
        {"art": art, "nummer": "1", "datum": "06.10.2026"},
        [{"bezeichnung": "Ton", "menge": "1", "preis": "10"}],
    )

    dokument = dateien.dokument_holen(verbindung, dokument_id)
    assert dokument is not None

    ziel = tmp_path / f"{art}.pdf"
    pdf.erzeugen(verbindung, dokument, ziel)

    assert ziel.is_file()
