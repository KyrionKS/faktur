"""Tests für den Umzug des Datenbestands."""

from __future__ import annotations

from pathlib import Path

from faktur import db


def test_ordner_werden_angelegt(tmp_path: Path) -> None:
    """Der Datenordner und der Dokumentordner entstehen von selbst."""
    db.DATENORDNER = tmp_path / "daten"
    db.DATENBANK = db.DATENORDNER / "faktur.db"
    db.STANDARD_LOGO = db.DATENORDNER / "logo.png"
    db.DOKUMENTE = db.DATENORDNER / "Dokumente"
    db.ALT_DATENORDNER = tmp_path / "gibtsnicht"
    db.ALT_DOKUMENTE = tmp_path / "gibtsnicht"

    verbindung = db.verbinden()
    assert db.DATENORDNER.is_dir()
    assert db.DATENBANK.is_file()

    db.ausgabeordner()
    assert db.DOKUMENTE.is_dir()
    verbindung.close()


def test_umzug_holt_die_datenbank(tmp_path: Path) -> None:
    """Eine alte Datei wandert nach daten/."""
    alt = tmp_path / ".faktur"
    alt.mkdir()
    (alt / "faktur.db").write_bytes(b"alte datenbank")

    db.ALT_DATENORDNER = alt
    db.ALT_DOKUMENTE = tmp_path / "Rechnungen"
    db.DATENORDNER = tmp_path / "daten"
    db.DATENBANK = db.DATENORDNER / "faktur.db"
    db.DOKUMENTE = db.DATENORDNER / "Dokumente"

    meldungen = db.umziehen()

    assert (tmp_path / "daten" / "faktur.db").read_bytes() == b"alte datenbank"
    assert not (alt / "faktur.db").exists()
    assert meldungen, "Es kam keine Meldung fuer den Umzug."


def test_umzug_holt_die_pdf(tmp_path: Path) -> None:
    """Alte PDF landen im Dokumentordner."""
    alt = tmp_path / "Rechnungen"
    alt.mkdir()
    (alt / "ANG - 0001 - Testkunde.pdf").write_bytes(b"%PDF")

    db.ALT_DATENORDNER = tmp_path / "gibtsnicht"
    db.ALT_DOKUMENTE = alt
    db.DATENORDNER = tmp_path / "daten"
    db.DOKUMENTE = db.DATENORDNER / "Dokumente"

    db.umziehen()

    assert (db.DOKUMENTE / "ANG - 0001 - Testkunde.pdf").is_file()
    assert not (alt / "ANG - 0001 - Testkunde.pdf").exists()


def test_umzug_ist_nicht_mehr_ausfuehrbar_nach_einem_mal(tmp_path: Path) -> None:
    """Ein zweiter Start schiebt nichts noch einmal."""
    alt = tmp_path / ".faktur"
    alt.mkdir()
    (alt / "faktur.db").write_bytes(b"alt")

    db.ALT_DATENORDNER = alt
    db.ALT_DOKUMENTE = tmp_path / "Rechnungen"
    db.DATENORDNER = tmp_path / "daten"
    db.DATENBANK = db.DATENORDNER / "faktur.db"
    db.DOKUMENTE = db.DATENORDNER / "Dokumente"

    db.umziehen()
    # Ein neues Dokument an der alten Stelle darf nicht zurueckgeschoben
    # werden.
    (alt / "faktur.db").write_bytes(b"nochmal alt")
    meldungen = db.umziehen()

    assert db.DATENBANK.read_bytes() == b"alt"
    assert meldungen == []
