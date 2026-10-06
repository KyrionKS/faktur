"""Tests für den Umstieg einer alten Datenbank.

Vor der Vierstelligkeit trugen die Nummern ein Jahr und eine Folge, etwa
``2026-199``. Beim ersten Start werden sie umgeschrieben. Das rührt echte
Daten an, also wird es genau einmal gemacht und vorher gesichert.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from faktur import dateien, db


def _altdatei(pfad: Path, dokumente: list[tuple[str, str, str]]) -> None:
    """Baut eine Datenbank mit den Nummern von gestern.

    Args:
        pfad: Wohin die Datei soll.
        dokumente: Die Dokumente als Art, Nummer, Datum.
    """
    alt = sqlite3.connect(pfad)
    alt.executescript(db.SCHEMA)
    for art, nummer, datum in dokumente:
        alt.execute(
            "INSERT INTO dokumente (art, nummer, datum) VALUES (?, ?, ?)",
            (art, nummer, datum),
        )
    alt.commit()
    alt.close()


def _nummern_lesen(pfad: Path) -> list[tuple[str, str, str]]:
    """Öffnet die gewanderte Datei und liest alle Dokumente.

    Args:
        pfad: Die Datenbankdatei.

    Returns:
        Die Dokumente als Art, Nummer, Datum, neuestes zuerst.
    """
    verbindung = db.verbinden(pfad)
    gelesen = []
    for zeile in dateien.dokumente(verbindung):
        gelesen.append((zeile["art"], zeile["nummer"], zeile["datum"]))
    verbindung.close()
    return gelesen


def test_nummern_werden_auf_vier_stellen_geschrieben(tmp_path: Path) -> None:
    """Aus ``2026-199`` wird eine fortlaufende Nummer.

    Args:
        tmp_path: Das temporäre Verzeichnis von pytest.
    """
    pfad = tmp_path / "alt.db"
    _altdatei(
        pfad,
        [
            ("angebot", "2026-199", "01.10.2026"),
            ("rechnung", "2026-199", "02.10.2026"),
            ("angebot", "2026-200", "03.10.2026"),
        ],
    )

    assert _nummern_lesen(pfad) == [
        ("angebot", "0003", "03.10.2026"),
        ("rechnung", "0002", "02.10.2026"),
        ("angebot", "0001", "01.10.2026"),
    ]


def test_angebot_und_rechnung_bekommen_aufeinanderfolgende_nummern(
    tmp_path: Path,
) -> None:
    """Ein Angebot und seine Rechnung stehen nebeneinander.

    Args:
        tmp_path: Das temporäre Verzeichnis von pytest.
    """
    pfad = tmp_path / "paar.db"
    _altdatei(
        pfad,
        [("angebot", "2026-199", "01.10.2026"), ("rechnung", "2026-199", "02.10.2026")],
    )

    nach_nummer = {}
    for art, nummer, _datum in _nummern_lesen(pfad):
        nach_nummer[art] = nummer

    assert nach_nummer["angebot"] == "0001"
    assert nach_nummer["rechnung"] == "0002"


def test_positionen_bleiben_bei_den_dokumenten(tmp_path: Path) -> None:
    """Das Umschreiben fasst nur die Nummern an.

    Args:
        tmp_path: Das temporäre Verzeichnis von pytest.
    """
    pfad = tmp_path / "positionen.db"
    alt = sqlite3.connect(pfad)
    alt.executescript(db.SCHEMA)
    cursor = alt.execute(
        "INSERT INTO dokumente (art, nummer, datum) VALUES ('rechnung', ?, ?)",
        ("2026-199", "01.10.2026"),
    )
    dokument_id = cursor.lastrowid
    alt.execute(
        "INSERT INTO positionen (dokument_id, bezeichnung, menge, preis)"
        " VALUES (?, ?, ?, ?)",
        (dokument_id, "Aufnahme Ton", 2, 850.0),
    )
    alt.commit()
    alt.close()

    neu = db.verbinden(pfad)
    positionen = dateien.positionen(neu, dokument_id)

    assert len(positionen) == 1
    assert positionen[0]["bezeichnung"] == "Aufnahme Ton"
    assert dateien.summe_von(neu, dokument_id) == 1700.0
    neu.close()


def test_die_datei_wird_vorher_gesichert(tmp_path: Path) -> None:
    """Vor dem Umschreiben liegt eine Kopie der alten Datei.

    Args:
        tmp_path: Das temporäre Verzeichnis von pytest.
    """
    pfad = tmp_path / "sicherung.db"
    _altdatei(pfad, [("rechnung", "2026-199", "01.10.2026")])

    db.verbinden(pfad).close()

    sicherung = pfad.with_suffix(pfad.suffix + ".bak")
    assert sicherung.is_file()

    alt = sqlite3.connect(sicherung)
    nummer = alt.execute("SELECT nummer FROM dokumente").fetchone()[0]
    alt.close()

    assert nummer == "2026-199"


def test_die_wanderung_laeuft_nur_einmal(tmp_path: Path) -> None:
    """Beim zweiten Start bleiben neue Nummern stehen.

    Args:
        tmp_path: Das temporäre Verzeichnis von pytest.
    """
    pfad = tmp_path / "einmal.db"
    _altdatei(pfad, [("rechnung", "2026-199", "01.10.2026")])

    db.verbinden(pfad).close()

    zweite = db.verbinden(pfad)
    dateien.dokument_speichern(
        zweite, {"art": "rechnung", "nummer": "0042", "datum": "05.10.2026"}, []
    )
    zweite.close()

    gelesen = _nummern_lesen(pfad)
    assert sorted(nummer for _art, nummer, _datum in gelesen) == ["0001", "0042"]


def test_leere_datenbank_braucht_keine_sicherung(tmp_path: Path) -> None:
    """Ohne Dokumente gibt es nichts umzuschreiben und nichts zu sichern.

    Args:
        tmp_path: Das temporäre Verzeichnis von pytest.
    """
    pfad = tmp_path / "leer.db"

    db.verbinden(pfad).close()

    assert not pfad.with_suffix(pfad.suffix + ".bak").exists()


def test_index_verbietet_doppelte_nummern(tmp_path: Path) -> None:
    """Die Datenbank lässt keine doppelte Nummer mehr zu.

    Args:
        tmp_path: Das temporäre Verzeichnis von pytest.
    """
    verbindung = db.verbinden(tmp_path / "index.db")
    dateien.dokument_speichern(
        verbindung, {"art": "angebot", "nummer": "0001", "datum": "01.10.2026"}, []
    )

    with pytest.raises(sqlite3.IntegrityError):
        dateien.dokument_speichern(
            verbindung,
            {"art": "rechnung", "nummer": "0001", "datum": "02.10.2026"},
            [],
        )
    verbindung.close()
