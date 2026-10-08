"""Tests für die Auswahl der Blöcke.

Das Wichtigste hier steht in :data:`GEWOLLT`: die Voreinstellung muss genau
das ergeben, was vor dieser Funktion fest im Programm stand. Sonst würde ein
Programmwechsel das Aussehen schon erzeugter und noch nicht erzeugter
Angebote ändern, ohne dass jemand etwas getan hätte.
"""

from __future__ import annotations

import sqlite3

import pytest
from faktur import bloecke

#: So sah es vor der Auswahl aus, abgelesen aus pdf.py:
#: Bank, Steuernummer und Zahlhinweis standen fest auf „nur Rechnung".
GEWOLLT = {
    "angebot": {
        "firma",
        "zusatz",
        "anschrift",
        "telefon",
        "email",
        "logo",
        "inhaber",
        "firmenzeile",
        "seitenzahl",
    },
    "rechnung": {
        "firma",
        "zusatz",
        "anschrift",
        "telefon",
        "email",
        "logo",
        "zahlbar",
        "bank",
        "steuer",
        "inhaber",
        "firmenzeile",
        "seitenzahl",
    },
}


@pytest.mark.parametrize("art", sorted(GEWOLLT))
def test_die_voreinstellung_ergibt_das_alte_dokument(
    verbindung: sqlite3.Connection, art: str
) -> None:
    """Ohne jede Einstellung kommt das Dokument von heute heraus.

    Args:
        verbindung: Eine frische Datenbank ohne die Auswahl.
        art: Die Dokumentart.
    """
    assert bloecke.ausgabe(verbindung, art) == GEWOLLT[art]


def test_auf_der_rechnung_ist_alles_an_ausser_der_webseite() -> None:
    """Die Rechnung ist vollständig, und zwar mit Absicht.

    Einzige Ausnahme ist die Webseite, weil sie auf keinem Dokument von
    heute stand. Wer sie einschaltet, holt sie zum ersten Mal aufs Papier.

    Der Schutz ist der Wegfall, nicht ein Verbot: wer die Bankverbindung
    abschaltet, hat eine Rechnung, auf der niemand zahlen kann, und das
    ist eine bewusste Entscheidung.
    """
    erwartet = frozenset(bloecke.NAMEN) - {"webseite"}
    assert bloecke.voreinstellung("rechnung") == erwartet


@pytest.mark.parametrize("name", ["bank", "steuer", "zahlbar"])
def test_auf_dem_angebot_steht_keine_bankverbindung(name: str) -> None:
    """Diese drei standen nie auf einem Angebot.

    Args:
        name: Der Name des Blocks.
    """
    assert name not in bloecke.voreinstellung("angebot")
    assert name in bloecke.voreinstellung("rechnung")


def test_die_webseite_stand_noch_auf_keinem_dokument() -> None:
    """Sie war im Formular, aber sie kam nie auf die PDF.

    Deshalb ist sie aus, obwohl sie in den Stammdaten steht. Wer sie
    einschaltet, holt sie zum ersten Mal aufs Papier.
    """
    assert "webseite" not in bloecke.voreinstellung("angebot")
    assert "webseite" not in bloecke.voreinstellung("rechnung")


def test_jeder_block_gehoert_genau_einem_ort() -> None:
    """Sonst wüsste das Programm nicht, wo er hingehört."""
    orte = {block.ort for block in bloecke.BLOECKE}
    assert orte == {bloecke.KOPF, bloecke.ABSCHLUSS, bloecke.FUSS}


def test_die_namen_sind_eindeutig() -> None:
    """Zwei Blöcke mit demselben Namen würden sich gegenseitig abschalten."""
    assert len(set(bloecke.NAMEN)) == len(bloecke.NAMEN)


def test_jeder_block_hat_einen_titel() -> None:
    """Sonst stünde im Menü eine leere Zeile."""
    assert all(block.titel.strip() for block in bloecke.BLOECKE)


def test_das_programm_kennt_nur_die_vorhandenen_bloecke(
    verbindung: sqlite3.Connection,
) -> None:
    """Namen, die es nicht gibt, werden überlesen.

    Eine Einstellung aus einer künftigen Version darf kein Programm von
    heute lahmlegen.

    Args:
        verbindung: Eine frische Datenbank.
    """
    from faktur import einstellungen

    einstellungen.speichere(
        verbindung, bloecke.schluessel("rechnung"), "firma,unsinn,logo,auch nicht"
    )

    assert bloecke.ausgabe(verbindung, "rechnung") == {"firma", "logo"}


@pytest.mark.parametrize("wert", ["", "   ", "\n"])
def test_ein_leerer_wert_heisst_voreinstellung_und_nicht_nichts(
    verbindung: sqlite3.Connection, wert: str
) -> None:
    """Wer die Auswahl leert, bekommt nicht plötzlich ein leeres Dokument.

    Das wäre der gefährlichste Fehler der ganzen Funktion: eine Rechnung
    ohne Firmenzeile und ohne Bankverbindung sieht aus, als sei sie fertig.

    Args:
        verbindung: Eine frische Datenbank.
        wert: Der gespeicherte Wert.
    """
    from faktur import einstellungen

    einstellungen.speichere(verbindung, bloecke.schluessel("rechnung"), wert)

    assert bloecke.ausgabe(verbindung, "rechnung") == bloecke.voreinstellung("rechnung")


def test_gespeichert_wird_in_fester_reihenfolge(
    verbindung: sqlite3.Connection,
) -> None:
    """Nicht in der Reihenfolge des Klickens.

    Sonst stünde in der Einstellung später ``seitenzahl,firma,logo`` und
    niemand könnte es lesen.

    Args:
        verbindung: Eine frische Datenbank.
    """
    bloecke.speichere(verbindung, "angebot", frozenset({"seitenzahl", "firma", "logo"}))

    from faktur import einstellungen

    assert (
        einstellungen.hole(verbindung, bloecke.schluessel("angebot"))
        == "firma,logo,seitenzahl"
    )


def test_speichern_und_lesen_passen_zusammen(
    verbindung: sqlite3.Connection,
) -> None:
    """Der ganze Weg von der Auswahl bis zur PDF.

    Args:
        verbindung: Eine frische Datenbank.
    """
    gewaehlt = frozenset({"firma", "anschrift", "logo"})
    bloecke.speichere(verbindung, "rechnung", gewaehlt)

    assert bloecke.ausgabe(verbindung, "rechnung") == gewaehlt


def test_die_arten_bekommen_ihren_eigenen_schluessel(
    verbindung: sqlite3.Connection,
) -> None:
    """Angebot und Rechnung sind unabhängig voneinander.

    Args:
        verbindung: Eine frische Datenbank.
    """
    bloecke.speichere(verbindung, "angebot", frozenset({"firma"}))

    assert bloecke.schluessel("angebot") != bloecke.schluessel("rechnung")
    assert bloecke.ausgabe(verbindung, "angebot") == {"firma"}
    assert bloecke.ausgabe(verbindung, "rechnung") == bloecke.voreinstellung("rechnung")


def test_leerzeichen_und_doppelte_werden_ignoriert(
    verbindung: sqlite3.Connection,
) -> None:
    """Ein von Hand gesetzter Wert darf nicht versagen.

    Args:
        verbindung: Eine frische Datenbank.
    """
    from faktur import einstellungen

    einstellungen.speichere(
        verbindung, bloecke.schluessel("angebot"), " firma , logo ,,firma, "
    )

    assert bloecke.ausgabe(verbindung, "angebot") == {"firma", "logo"}


def test_gehoert_fragt_einen_einzelnen_block(
    verbindung: sqlite3.Connection,
) -> None:
    """Die Kurzform, die das Programm überall benutzt.

    Args:
        verbindung: Eine frische Datenbank.
    """
    assert bloecke.gehoert(verbindung, "rechnung", "bank") is True
    assert bloecke.gehoert(verbindung, "angebot", "bank") is False


@pytest.mark.parametrize("art", ["Angebot", "RECHNUNG", " rechnung "])
def test_gross_klein_und_leerzeichen_stoeren_nicht(art: str) -> None:
    """Der Schluessel darf nicht davon abhaengen, wie man ihn schreibt.

    Args:
        art: Die Art in irgendeiner Schreibweise.
    """
    assert bloecke.schluessel(art) == f"ausgabe_{art.strip().lower()}"


@pytest.mark.parametrize("art", ["rechnung", "angebot"])
def test_eine_unbekannte_art_wird_abgewiesen(art: str) -> None:
    """Sonst entstünde ein Schlüssel, den niemand liest.

    Args:
        art: Eine gültige Art, mit einem Buchstaben angehängt.
    """
    db = sqlite3.connect(":memory:")

    with pytest.raises(KeyError):
        bloecke.voreinstellung(art + "x")

    with pytest.raises(KeyError):
        bloecke.speichere(db, art + "x", frozenset({"firma"}))

    db.close()
