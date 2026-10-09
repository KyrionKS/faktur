"""Tests für das Lesen und Schreiben in der Datenbank."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from faktur import dateien, db


def test_startleistungen_sind_da(verbindung: sqlite3.Connection) -> None:
    """Eine neue Datenbank bekommt die Leistungen des Tonstudios."""
    liste = dateien.leistungen(verbindung)
    namen = {zeile["bezeichnung"] for zeile in liste}
    assert "Aufnahme Ton" in namen
    assert "Mischung und Mastering" in namen
    assert len(liste) == len(db.STARTLEISTUNGEN)


def test_startleistungen_werden_nicht_ueberschrieben(tmp_path: Path) -> None:
    """Ein zweiter Start legt die Leistungen nicht noch einmal an.

    Args:
        tmp_path: Das temporäre Verzeichnis von pytest.
    """
    pfad = tmp_path / "zweimal.db"

    erste = db.verbinden(pfad)
    leistung = dateien.leistungen(erste)[0]
    bezeichnung = leistung["bezeichnung"]
    dateien.leistung_speichern(
        erste,
        {"bezeichnung": bezeichnung, "preis": "1234,00"},
        leistung_id=leistung["id"],
    )
    erste.close()

    zweite = db.verbinden(pfad)
    erneut = dateien.leistungen(zweite)
    preis = zweite.execute(
        "SELECT preis FROM leistungen WHERE bezeichnung = ?", (bezeichnung,)
    ).fetchone()
    zweite.close()

    assert len(erneut) == len(db.STARTLEISTUNGEN)
    assert preis is not None
    assert preis["preis"] == 1234.0


def test_kunde_anlegen_und_aendern(verbindung: sqlite3.Connection) -> None:
    """Legt einen Kunden an und überschreibt seine Felder."""
    nummer = dateien.kunde_speichern(
        verbindung,
        {
            "firma": "Soundcheck GmbH",
            "ansprechpartner": "Max Mustermann",
            "ort": "Berlin",
            "plz": "12345",
        },
    )

    kunde = dateien.kunde_holen(verbindung, nummer)
    assert kunde is not None
    assert kunde["firma"] == "Soundcheck GmbH"

    dateien.kunde_speichern(verbindung, {"firma": "Soundcheck AG"}, nummer)
    geaendert = dateien.kunde_holen(verbindung, nummer)
    assert geaendert is not None
    assert geaendert["firma"] == "Soundcheck AG"


def test_kunden_sortieren_nach_firma(verbindung: sqlite3.Connection) -> None:
    """Die Liste ist alphabetisch, unabhängig von der Eingabe."""
    for firma in ("Zeta Ton", "Alpha Studio", "Media Werk"):
        dateien.kunde_speichern(verbindung, {"firma": firma})

    namen = [kunde["firma"] for kunde in dateien.kunden(verbindung)]
    assert namen == sorted(namen, key=str.lower)


def test_kunde_loeschen_nimmt_dokumente_mit(
    verbindung: sqlite3.Connection,
) -> None:
    """Ein Kunde verschwindet samt seiner Angebote und Rechnungen."""
    kunde_id = dateien.kunde_speichern(verbindung, {"firma": "Weg GmbH"})
    dokument_id = dateien.dokument_speichern(
        verbindung,
        {
            "art": "rechnung",
            "nummer": "R-1",
            "kunde_id": kunde_id,
            "datum": "06.10.2026",
        },
        [{"bezeichnung": "Ton", "menge": "1", "preis": "100"}],
    )

    dateien.kunde_loeschen(verbindung, kunde_id)

    assert dateien.kunde_holen(verbindung, kunde_id) is None
    assert dateien.dokument_holen(verbindung, dokument_id) is None
    assert dateien.positionen(verbindung, dokument_id) == []


def test_dokument_summe_und_positionen(verbindung: sqlite3.Connection) -> None:
    """Rechnet die Summe aus Menge mal Preis."""
    dokument_id = dateien.dokument_speichern(
        verbindung,
        {"art": "angebot", "nummer": "A-1", "datum": "06.10.2026"},
        [
            {"bezeichnung": "Aufnahme", "menge": "2", "einheit": "Tag", "preis": "850"},
            {"bezeichnung": "Mischung", "menge": "10", "einheit": "h", "preis": "95"},
        ],
    )

    assert dateien.summe_von(verbindung, dokument_id) == pytest.approx(2650.0)
    assert len(dateien.positionen(verbindung, dokument_id)) == 2


def test_positionen_behalten_ihre_reihenfolge(verbindung: sqlite3.Connection) -> None:
    """Die Reihenfolge im Dokument ist die Reihenfolge in der Liste."""
    dokument_id = dateien.dokument_speichern(
        verbindung,
        {"art": "angebot", "nummer": "A-2", "datum": "06.10.2026"},
        [
            {"bezeichnung": "Erste", "preis": "1"},
            {"bezeichnung": "Zweite", "preis": "2"},
            {"bezeichnung": "Dritte", "preis": "3"},
        ],
    )

    namen = [p["bezeichnung"] for p in dateien.positionen(verbindung, dokument_id)]
    assert namen == ["Erste", "Zweite", "Dritte"]


def test_doppelte_nummer_wird_angenommen(verbindung: sqlite3.Connection) -> None:
    """Zwei Rechnungen mit derselben Nummer gehen.

    Die Nummer ist eine Projektnummer und gehoert dem Benutzer. Das Programm
    prueft sie nicht, und seit 0.9.0 gibt es auch keinen Index mehr, der es
    koennte.

    Args:
        verbindung: Die Testdatenbank.
    """
    dateien.dokument_speichern(
        verbindung, {"art": "rechnung", "nummer": "0199", "datum": "06.10.2026"}, []
    )
    dateien.dokument_speichern(
        verbindung,
        {"art": "rechnung", "nummer": "0199", "datum": "20.10.2026"},
        [],
    )

    assert len(dateien.dokumente(verbindung, "rechnung")) == 2


def test_gleiche_nummer_fuer_angebot_und_rechnung_geht(
    verbindung: sqlite3.Connection,
) -> None:
    """Angebot und Rechnung eines Projekts tragen dieselbe Nummer.

    Das ist der eigentliche Zweck: Aus Angebot 0199 wird Rechnung 0199, weil
    beide zum selben Projekt gehoeren. Bis 0.8.2 stand hier ein
    ``UNIQUE``-Index, und genau das war der Fall, den der Benutzer nicht
    konnte.

    Args:
        verbindung: Die Testdatenbank.
    """
    dateien.dokument_speichern(
        verbindung, {"art": "angebot", "nummer": "0199", "datum": "06.10.2026"}, []
    )
    dateien.dokument_speichern(
        verbindung, {"art": "rechnung", "nummer": "0199", "datum": "20.10.2026"}, []
    )

    dokumente = dateien.dokumente(verbindung)
    assert [d["art"] for d in dokumente] == ["rechnung", "angebot"]
    assert {d["nummer"] for d in dokumente} == {"0199"}, (
        "Beide Dokumente muessen dieselbe Nummer tragen."
    )


def test_zaehler_zaehlt_ueber_beide_arten(verbindung: sqlite3.Connection) -> None:
    """Der Zähler läuft durch, er beginnt nicht je Art neu.

    Args:
        verbindung: Die Testdatenbank.
    """
    assert dateien.naechste_nummer(verbindung) == "0001"

    dateien.dokument_speichern(
        verbindung, {"art": "angebot", "nummer": "0001", "datum": "06.10.2026"}, []
    )
    assert dateien.naechste_nummer(verbindung) == "0002"

    dateien.dokument_speichern(
        verbindung, {"art": "rechnung", "nummer": "0002", "datum": "07.10.2026"}, []
    )
    assert dateien.naechste_nummer(verbindung) == "0003"


def test_zaehler_springt_ueber_freie_nummern(verbindung: sqlite3.Connection) -> None:
    """Der Vorschlag ist die höchste vergebene plus eins.

    Args:
        verbindung: Die Testdatenbank.
    """
    for nummer in ("0001", "0007"):
        dateien.dokument_speichern(
            verbindung,
            {"art": "rechnung", "nummer": nummer, "datum": "06.10.2026"},
            [],
        )

    assert dateien.naechste_nummer(verbindung) == "0008"


def test_zaehler_ignoriert_alte_nummern_mit_jahr(
    verbindung: sqlite3.Connection,
) -> None:
    """Eine Zahl wie 2026-199 zählt nicht mit.

    Solche Nummern gab es vorher. Sie enthalten keine Zahl, die man als
    Zählerstand lesen könnte, also dürfen sie den Vorschlag nicht verschieben.

    Args:
        verbindung: Die Testdatenbank.
    """
    dateien.dokument_speichern(
        verbindung,
        {"art": "rechnung", "nummer": "2026-199", "datum": "06.10.2026"},
        [],
    )

    assert dateien.naechste_nummer(verbindung) == "0001"


def test_dokument_aendern_ersetzt_die_positionen(
    verbindung: sqlite3.Connection,
) -> None:
    """Beim Ändern bleibt keine alte Position zurück.

    Args:
        verbindung: Die Testdatenbank.
    """
    dokument_id = dateien.dokument_speichern(
        verbindung,
        {"art": "angebot", "nummer": "A-3", "datum": "06.10.2026"},
        [
            {"bezeichnung": "Alt", "preis": "10"},
            {"bezeichnung": "Eher alt", "preis": "20"},
        ],
    )

    dateien.dokument_speichern(
        verbindung,
        {
            "art": "angebot",
            "nummer": "A-3",
            "datum": "06.10.2026",
            "dokument_id": dokument_id,
        },
        [{"bezeichnung": "Neu", "preis": "30"}],
    )

    positionen = dateien.positionen(verbindung, dokument_id)
    assert [p["bezeichnung"] for p in positionen] == ["Neu"]


def test_angebot_wird_zur_rechnung(verbindung: sqlite3.Connection) -> None:
    """Übernimmt die Positionen aus dem Angebot."""
    kunde_id = dateien.kunde_speichern(verbindung, {"firma": "Film AG"})
    leistung_id = dateien.leistungen(verbindung)[0]["id"]

    angebot_id = dateien.dokument_speichern(
        verbindung,
        {
            "art": "angebot",
            "nummer": "ANG-1",
            "kunde_id": kunde_id,
            "datum": "06.10.2026",
            "notiz": "Bitte freundlich formulieren",
        },
        [
            {
                "leistung_id": leistung_id,
                "bezeichnung": "Aufnahme Ton",
                "menge": "2",
                "preis": "850",
            }
        ],
    )

    kopf, positionen = dateien.als_angebot_uebernehmen(verbindung, angebot_id)

    assert kopf["art"] == "rechnung"
    assert kopf["kunde_id"] == kunde_id
    assert kopf["notiz"] == "Bitte freundlich formulieren"
    assert len(positionen) == 1
    assert positionen[0]["bezeichnung"] == "Aufnahme Ton"
    assert positionen[0]["leistung_id"] == leistung_id


def test_nur_aus_einem_angebot_lässt_sich_eine_rechnung_machen(
    verbindung: sqlite3.Connection,
) -> None:
    """Eine Rechnung ist keine Rechnung.

    Args:
        verbindung: Die Testdatenbank.
    """
    rechnung_id = dateien.dokument_speichern(
        verbindung, {"art": "rechnung", "nummer": "R-9", "datum": "06.10.2026"}, []
    )

    with pytest.raises(ValueError, match="Angebot"):
        dateien.als_angebot_uebernehmen(verbindung, rechnung_id)


def test_leistung_loeschen_behaelt_alte_dokumente(
    verbindung: sqlite3.Connection,
) -> None:
    """Alte Rechnungen verlieren ihre Position nicht.

    Args:
        verbindung: Die Testdatenbank.
    """
    leistung_id = dateien.leistungen(verbindung)[0]["id"]
    dokument_id = dateien.dokument_speichern(
        verbindung,
        {"art": "rechnung", "nummer": "R-2", "datum": "06.10.2026"},
        [{"leistung_id": leistung_id, "bezeichnung": "Ton", "preis": "850"}],
    )

    dateien.leistung_loeschen(verbindung, leistung_id)

    positionen = dateien.positionen(verbindung, dokument_id)
    assert len(positionen) == 1
    assert positionen[0]["bezeichnung"] == "Ton"
    assert positionen[0]["preis"] == 850.0
    assert positionen[0]["leistung_id"] is None


def test_angebot_wird_zur_rechnung_mit_alle_positionen(
    verbindung: sqlite3.Connection,
) -> None:
    """Beim Umwandeln darf keine Position verloren gehen.

    Args:
        verbindung: Die Testdatenbank.
    """
    kunde_id = dateien.kunde_speichern(verbindung, {"firma": "Film AG"})
    leistungen = dateien.leistungen(verbindung)
    ton = leistungen[0]
    mischung = leistungen[1]

    angebot_id = dateien.dokument_speichern(
        verbindung,
        {
            "art": "angebot",
            "nummer": "0001",
            "kunde_id": kunde_id,
            "datum": "01.10.2026",
            "gueltig_bis": "22.10.2026",
            "notiz": "Angebot gilt drei Wochen.",
        },
        [
            {
                "leistung_id": ton["id"],
                "bezeichnung": ton["bezeichnung"],
                "menge": "2",
                "einheit": "Tag",
                "preis": "850",
            },
            {
                "leistung_id": mischung["id"],
                "bezeichnung": mischung["bezeichnung"],
                "menge": "10",
                "einheit": "Stunde",
                "preis": "95",
            },
        ],
    )

    kopf, positionen = dateien.als_angebot_uebernehmen(verbindung, angebot_id)

    rechnung_id = dateien.dokument_speichern(verbindung, kopf, positionen)
    rechnung = dateien.dokument_holen(verbindung, rechnung_id)

    assert rechnung is not None
    assert rechnung["art"] == "rechnung"
    assert rechnung["kunde_id"] == kunde_id
    assert rechnung["notiz"] == "Angebot gilt drei Wochen."
    # Datum und Fälligkeit bleiben leer, die kommen in der Kontrolle dazu.
    assert rechnung["datum"] == ""
    assert rechnung["faellig"] == ""

    uebernommen = dateien.positionen(verbindung, rechnung_id)
    assert len(uebernommen) == 2
    assert [p["bezeichnung"] for p in uebernommen] == [
        ton["bezeichnung"],
        mischung["bezeichnung"],
    ]
    assert dateien.summe_von(verbindung, rechnung_id) == 2650.0
    # Die Verknüpfung zur Preisliste bleibt, damit später zugeordnet
    # werden kann, welcher Preis zu welcher Leistung gehört.
    assert uebernommen[0]["leistung_id"] == ton["id"]


def test_angebot_bleibt_beim_umwandeln_bestehen(
    verbindung: sqlite3.Connection,
) -> None:
    """Das Angebot wird nicht verbraucht, es bleibt als Beleg stehen.

    Args:
        verbindung: Die Testdatenbank.
    """
    kunde_id = dateien.kunde_speichern(verbindung, {"firma": "Werbe GmbH"})
    angebot_id = dateien.dokument_speichern(
        verbindung,
        {
            "art": "angebot",
            "nummer": "0001",
            "kunde_id": kunde_id,
            "datum": "01.10.2026",
        },
        [{"bezeichnung": "Jingle", "menge": "1", "preis": "450"}],
    )

    kopf, positionen = dateien.als_angebot_uebernehmen(verbindung, angebot_id)
    dateien.dokument_speichern(verbindung, kopf, positionen)

    assert dateien.dokument_holen(verbindung, angebot_id) is not None
    assert len(dateien.positionen(verbindung, angebot_id)) == 1
