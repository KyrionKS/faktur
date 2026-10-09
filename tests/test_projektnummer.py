"""Die Nummer ist eine Projektnummer.

Bis 0.8.2 musste die Nummer für sich allein eindeutig sein: Ein ``UNIQUE``-Index
lag auf ``dokumente.nummer``, und das Programm lehnte jede Nummer ab, die
schon vergeben war. Daraus folgte, dass ein Angebot und eine Rechnung nicht
dieselbe Nummer tragen durften.

Das war falsch. Die Nummer ist eine **Projektnummer**, und ein Projekt hat ein
Angebot *und* eine Rechnung. Angebot 0199 und Rechnung 0199 sind ein Vorgang,
nicht zwei. Die Projektnummern vergibt der Benutzer selbst; das Programm
prüft sie nicht und warnt nicht.

Hier steht, was daraus folgt:

- Ein Angebot darf zweimal dieselbe Nummer tragen wie seine Rechnung.
- Beim Abrechnen wandert die Nummer vom Angebot auf die Rechnung, damit das
  Projekt an einer Nummer erkennbar bleibt.
- Die Nummern werden **nicht** auf Eindeutigkeit geprüft und es gibt keinen
  Index mehr, der es könnte.
- Angebot und Rechnung ergeben verschiedene Dateinamen, weil ``ANG`` und ``RE``
  den Namen unterscheiden. Zwei **Angebote** mit derselben Nummer tun das
  nicht — und darüber wird vor dem Schreiben nachgefragt.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from faktur import dateien, db


@pytest.fixture
def kunde(verbindung: sqlite3.Connection) -> int:
    """Legt einen Kunden an.

    Args:
        verbindung: Die Datenbankverbindung.

    Returns:
        Die Kennung des Kunden.
    """
    return dateien.kunde_speichern(verbindung, {"firma": "Tonstudio Nordwind"})


# ------------------------------------------- die Nummer wandert beim Abrechnen


def test_die_umwandlung_behaelt_die_projektnummer(
    verbindung: sqlite3.Connection, kunde: int
) -> None:
    """Aus Angebot 0199 wird Rechnung 0199.

    Args:
        verbindung: Die Datenbankverbindung.
        kunde: Die Kennung des Kunden.

    Raises:
        AssertionError: Wenn die Rechnung eine andere Nummer bekaemt.
    """
    angebot = dateien.dokument_speichern(
        verbindung,
        {"art": "angebot", "nummer": "0199", "kunde_id": kunde, "datum": "06.10.2026"},
        [
            {
                "bezeichnung": "Aufnahme Ton",
                "menge": "1",
                "einheit": "Tag",
                "preis": "850",
            }
        ],
    )

    kopf, positionen = dateien.als_angebot_uebernehmen(verbindung, angebot)

    assert kopf["nummer"] == "0199", (
        f"Die Rechnung bekommt die Nummer {kopf['nummer']!r} statt 0199. Bis "
        "0.8.2 stand hier ein leeres Feld, und es wurde die naechste freie "
        "vorgeschlagen — aus einem Projekt wurden dadurch zwei."
    )
    assert positionen, "Die Positionen müssen mitwandern."


def test_und_das_projekt_bleibt_an_einer_nummer(
    verbindung: sqlite3.Connection, kunde: int
) -> None:
    """Nach dem Abrechnen gibt es zwei Dokumente mit derselben Nummer.

    Args:
        verbindung: Die Datenbankverbindung.
        kunde: Die Kennung des Kunden.
    """
    pos = [
        {"bezeichnung": "Aufnahme Ton", "menge": "1", "einheit": "Tag", "preis": "850"}
    ]
    angebot = dateien.dokument_speichern(
        verbindung,
        {"art": "angebot", "nummer": "0199", "kunde_id": kunde, "datum": "06.10.2026"},
        pos,
    )
    kopf, _positionen = dateien.als_angebot_uebernehmen(verbindung, angebot)
    dateien.dokument_speichern(verbindung, {**kopf, "datum": "20.10.2026"}, pos)

    dokumente = dateien.dokumente(verbindung)
    nummern = {d["nummer"] for d in dokumente}

    assert nummern == {"0199"}, f"Die Dokumente tragen {nummern}, nicht nur 0199."
    assert {d["art"] for d in dokumente} == {"angebot", "rechnung"}


def test_die_nummer_wird_auch_nicht_zurueckgehalten(
    verbindung: sqlite3.Connection, kunde: int
) -> None:
    """Eine vergebene Nummer wird nicht mehr gemeldet.

    Bis 0.8.2 stand im Kontrollschirm eine Sperre, und die Meldung lautete
    "Die Nummer 0199 ist schon vergeben". Die gehört dem Benutzer, also
    faellt sie weg — ganz ohne Ersatz.

    Args:
        verbindung: Die Datenbankverbindung.
        kunde: Die Kennung des Kunden.

    Raises:
        AssertionError: Wenn der Bildschirm doch noch sperrt.
    """
    quelle = (
        Path(__file__).resolve().parents[1] / "faktur" / "screens" / "dokumente.py"
    ).read_text(encoding="utf-8")

    assert "schon vergeben" not in quelle, (
        "Die Meldung steht noch im Code. Die Nummer ist eine Projektnummer "
        "und gehoert dem Benutzer."
    )
    assert "in dateien.nummern(self.db)" not in quelle, (
        "Es wird noch gegen die vergebenen Nummern geprueft."
    )


def test_und_es_giebt_keinen_index_mehr(verbindung: sqlite3.Connection) -> None:
    """Die Datenbank traegt die Sperre nicht mehr.

    Args:
        verbindung: Die Datenbankverbindung.

    Raises:
        AssertionError: Wenn der Index noch liegt.
    """
    namen = {zeile[1] for zeile in verbindung.execute("PRAGMA index_list(dokumente)")}

    assert "dokumente_nummer_eindeutig" not in namen


# ------------------------------------------------------ die Dateinamen


def test_angebot_und_rechnung_heißen_trotz_gleicher_nummer_verschieden(
    verbindung: sqlite3.Connection, kunde: int
) -> None:
    """``ANG`` und ``RE`` unterscheiden die beiden Dateien.

    Das ist der Grund, warum diese Kuerzel im Namen stehen. Ohne sie hiessen
    die beiden Dateien eines Projekts gleich und die zweite wuerde die erste
    ersetzen.

    Args:
        verbindung: Die Datenbankverbindung.
        kunde: Die Kennung des Kunden.

    Raises:
        AssertionError: Wenn beide Namen gleich sind.
    """
    pos = [
        {"bezeichnung": "Aufnahme Ton", "menge": "1", "einheit": "Tag", "preis": "850"}
    ]
    angebot = dateien.dokument_speichern(
        verbindung,
        {"art": "angebot", "nummer": "0199", "kunde_id": kunde, "datum": "06.10.2026"},
        pos,
    )
    kopf, _p = dateien.als_angebot_uebernehmen(verbindung, angebot)
    rechnung = dateien.dokument_speichern(
        verbindung, {**kopf, "datum": "20.10.2026"}, pos
    )

    a = dateien.dokument_holen(verbindung, angebot)
    r = dateien.dokument_holen(verbindung, rechnung)

    name_angebot = dateien.dateiname(a, "angebot", "0199")
    name_rechnung = dateien.dateiname(r, "rechnung", "0199")

    assert name_angebot == "ANG - 0199 - Tonstudio Nordwind"
    assert name_rechnung == "RE - 0199 - Tonstudio Nordwind"
    assert name_angebot != name_rechnung, (
        "Beide Dateien hiessen gleich. Die zweite wuerde die erste ersetzen."
    )


def test_zwei_angebote_mit_der_nummer_heißen_gleich(
    verbindung: sqlite3.Connection, kunde: int
) -> None:
    """Zwei Angebote ergeben denselben Namen — deshalb wird nachgefragt.

    Das ist der einzige Fall, in dem die Projektnummer wirklich wehtut, und
    der Grund fuer die Frage vor dem Schreiben.

    Args:
        verbindung: Die Datenbankverbindung.
        kunde: Die Kennung des Kunden.

    Raises:
        AssertionError: Wenn die Namen doch verschieden sind.
    """
    pos = [
        {"bezeichnung": "Aufnahme Ton", "menge": "1", "einheit": "Tag", "preis": "850"}
    ]
    eins = dateien.dokument_speichern(
        verbindung,
        {"art": "angebot", "nummer": "0199", "kunde_id": kunde, "datum": "06.10.2026"},
        pos,
    )
    zwei = dateien.dokument_speichern(
        verbindung,
        {"art": "angebot", "nummer": "0199", "kunde_id": kunde, "datum": "07.10.2026"},
        pos,
    )

    d1 = dateien.dokument_holen(verbindung, eins)
    d2 = dateien.dokument_holen(verbindung, zwei)

    assert dateien.dateiname(d1, "angebot", "0199") == dateien.dateiname(
        d2, "angebot", "0199"
    )


def test_und_davor_wird_gefragt(verbindung: sqlite3.Connection, tmp_path: Path) -> None:
    """Beim Speichern wird nachgefragt, wenn die Datei schon da ist.

    Args:
        verbindung: Die Datenbankverbindung.
        tmp_path: Das temporaere Verzeichnis.

    Raises:
        AssertionError: Wenn nicht nachgefragt wird.
    """
    quelle = (
        Path(__file__).resolve().parents[1] / "faktur" / "screens" / "dokumente.py"
    ).read_text(encoding="utf-8")

    assert "is_file()" in quelle, "Es wird nicht geprueft, ob die Datei schon da ist."
    assert "gibt es schon" in quelle, "Es wird nicht nachgefragt."
    assert "Ueberschreiben" in quelle, "Die Frage sagt nicht, was passiert."

    del verbindung, tmp_path


def test_und_neu_schreiben_fragt_nicht(
    verbindung: sqlite3.Connection, tmp_path: Path
) -> None:
    """„PDF neu schreiben" soll ja ueberschreiben.

    Args:
        verbindung: Die Datenbankverbindung.
        tmp_path: Das temporaere Verzeichnis.

    Raises:
        AssertionError: Wenn auch dort nachgefragt wird.
    """
    del verbindung, tmp_path

    quelle = (
        Path(__file__).resolve().parents[1] / "faktur" / "screens" / "dokumente.py"
    ).read_text(encoding="utf-8")
    neu = quelle[quelle.index("def markiertes_dokument_schreiben") :][:1200]

    assert "gibt es schon" not in neu, (
        "Auch beim bewussten Neu-Schreiben wird nachgefragt. Das nervt."
    )


# ------------------------------------ dateiname liegt an der richtigen Stelle


def test_dateiname_liegt_in_dateien_und_nicht_im_bildschirm() -> None:
    """`aussehen.py` rief eine Funktion auf, die es dort nicht gab.

    `F2` auf dem Aussehen-Bildschirm sagte daraufhin „Konnte nicht schreiben:
    module 'faktur.dateien' has no attribute 'dateiname'“ — der `except
    Exception` hatte es verschluckt. Die Funktion stand in
    `screens/dokumente.py` und gehoert nach `dateien.py`.

    Raises:
        AssertionError: Wenn sie am falschen Ort liegt oder fehlt.
    """
    wurzel = Path(__file__).resolve().parents[1]

    assert hasattr(dateien, "dateiname"), (
        "dateiname gehoert nach dateien.py — zwei Bildschirme brauchen sie."
    )

    dokumente = (wurzel / "faktur" / "screens" / "dokumente.py").read_text(
        encoding="utf-8"
    )
    assert "def dateiname" not in dokumente, (
        "Die Funktion steht noch im Bildschirm und nicht in dateien.py."
    )

    aussehen = (wurzel / "faktur" / "screens" / "aussehen.py").read_text(
        encoding="utf-8"
    )
    assert "dateien.dateiname(" in aussehen, (
        "Der Aussehen-Bildschirm ruft sie nicht richtig auf — F2 waere stumm kaputt."
    )


def test_und_kein_bildschirm_behauptet_einen_falschen_import() -> None:
    """Kein `dateien.X`, das es nicht gibt.

    Mein Toter-Code-Scan aus 0.8 hat den Absturz vom Aussehen-Bildschirm
    uebersehen: Er zaehlte `dateiname` als *referenziert*, nicht als
    *vorhanden*. Genau der Unterschied ist der Fehler.

    Raises:
        AssertionError: Wenn ein Aufruf ins Leere zeigt.
    """
    import ast

    wurzel = Path(__file__).resolve().parents[1]
    gefunden: list[str] = []

    for datei in sorted((wurzel / "faktur").rglob("*.py")):
        modul = datei.stem
        quelle = datei.read_text(encoding="utf-8")
        try:
            baum = ast.parse(quelle)
        except SyntaxError:
            continue

        # Nur, wenn das Modul nicht selbst das Ziel ist.
        for knoten in ast.walk(baum):
            if (
                isinstance(knoten, ast.Attribute)
                and isinstance(knoten.value, ast.Name)
                and knoten.value.id == "dateien"
                and modul != "dateien"
                and not hasattr(dateien, knoten.attr)
            ):
                gefunden.append(f"{datei.name}:{knoten.lineno} dateien.{knoten.attr}")

    assert gefunden == [], (
        "Diese Aufrufe zeigen ins Leere — beim Benutzen gibt es einen "
        f"AttributeError: {gefunden}"
    )


# ----------------------------------------------- der Zaehler bleibt ein Vorschlag


def test_der_vorschlag_ist_keine_sperre(
    verbindung: sqlite3.Connection, kunde: int
) -> None:
    """Der Vorschlag darf nichts verschieben.

    `naechste_nummer` schlaegt die hoechste vergebene plus eins vor. Er
    blockiert nichts, und er muss auch nichts anbieten, wenn eine Projektnummer
    schon vergeben ist — das ist dann die des Benutzers.

    Args:
        verbindung: Die Datenbankverbindung.
        kunde: Die Kennung des Kunden.

    Raises:
        AssertionError: Wenn der Vorschlag von der Nummer abhaengt.
    """
    pos = [
        {"bezeichnung": "Aufnahme Ton", "menge": "1", "einheit": "Tag", "preis": "850"}
    ]
    dateien.dokument_speichern(
        verbindung,
        {"art": "angebot", "nummer": "0199", "kunde_id": kunde, "datum": "06.10.2026"},
        pos,
    )

    assert dateien.naechste_nummer(verbindung) == "0200"

    # Auch mit zwei Dokumenten auf 0199 bleibt der Sprung derselbe.
    dateien.dokument_speichern(
        verbindung,
        {"art": "rechnung", "nummer": "0199", "kunde_id": kunde, "datum": "20.10.2026"},
        pos,
    )

    assert dateien.naechste_nummer(verbindung) == "0200", (
        "Der Vorschlag hat sich durch die zweite Nummer verschoben."
    )


def test_und_der_weg_mit_der_datenbank_funktioniert_weiter(tmp_path: Path) -> None:
    """Eine bestehende Datenbank verliert die Sperre beim Start.

    Args:
        tmp_path: Das temporaere Verzeichnis.

    Raises:
        AssertionError: Wenn die Sperre liegen bleibt.
    """
    pfad = tmp_path / "alt.db"

    verbindung = db.verbinden(pfad)
    verbindung.execute(
        "CREATE UNIQUE INDEX dokumente_nummer_eindeutig ON dokumente (nummer)"
    )
    verbindung.commit()
    verbindung.close()

    zweite = db.verbinden(pfad)
    try:
        dateien.dokument_speichern(
            zweite, {"art": "angebot", "nummer": "0199", "datum": "01.10.2026"}, []
        )
        dateien.dokument_speichern(
            zweite, {"art": "rechnung", "nummer": "0199", "datum": "02.10.2026"}, []
        )
    finally:
        zweite.close()

    dritte = db.verbinden(pfad)
    try:
        assert len(dateien.dokumente(dritte)) == 2
    finally:
        dritte.close()
