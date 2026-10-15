"""Die Übersicht: was man am Anfang wissen will.

Es geht um drei Zahlen und darum, dass jede von ihnen **irgendwohin
führt**. Eine Zahl, die man nur ablesen kann, ist ein Bildschirmmuster;
eine, hinter der etwas liegt, ist eine Tür.

**Und um den Stichtag, nicht um das Zahlungsdatum.** Gefragt ist, was in
einem Monat in Rechnung gestellt wurde. Wer wissen will, was wirklich
hereingekommen ist, findet das bei den offenen Forderungen — dort steht
jede Rechnung mit ihrem Zahlungsdatum.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

from faktur import betraege, dateien, einstellungen  # noqa: E402
from faktur.gui.fenster import BEREICHE, Fenster  # noqa: E402
from faktur.gui.uebersicht import MONATE  # noqa: E402


@pytest.fixture
def app() -> object:
    """Gibt die laufende Qt-Anwendung zurück.

    Returns:
        Die Anwendung.
    """
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def db(tmp_path: Path) -> sqlite3.Connection:
    """Legt eine frische Datenbank mit einem Kunden an.

    Args:
        tmp_path: Das temporäre Verzeichnis.

    Returns:
        Die offene Verbindung.
    """
    from faktur import db as datenbank

    verbindung = datenbank.verbinden(tmp_path / "uebersicht.db")
    dateien.kunde_speichern(verbindung, {"firma": "Soundcheck GmbH"})
    einstellungen.speichere(verbindung, "firma", "New Air Media Group")
    einstellungen.speichere(verbindung, "iban", "DE02 1203 0000 0000 2020 51")
    return verbindung


def _rechnung(
    db: sqlite3.Connection,
    preis: str,
    nummer: str = "0001",
    tag: str | None = None,
    faellig: str = "31.12.2099",
    bezahlt: str = "",
) -> int:
    """Legt eine Rechnung an.

    Args:
        db: Die Datenbankverbindung.
        preis: Der Stückpreis.
        nummer: Die Projektnummer.
        tag: Das Datum. Ohne Angabe der heutige.
        faellig: Das Fälligkeitsdatum.
        bezahlt: Das Zahlungsdatum, leer für offen.

    Returns:
        Die Nummer der Rechnung.
    """
    return dateien.dokument_speichern(
        db,
        {
            "art": "rechnung",
            "nummer": nummer,
            "kunde_id": 1,
            "datum": tag or betraege.heute(),
            "faellig": faellig,
            "bezahlt_am": bezahlt,
        },
        [
            {
                "bezeichnung": "Aufnahme Ton",
                "menge": "1",
                "einheit": "Tag",
                "preis": preis,
            }
        ],
    )


def _angebot(db: sqlite3.Connection, preis: str = "400", nummer: str = "9000") -> int:
    """Legt ein Angebot an.

    Args:
        db: Die Datenbankverbindung.
        preis: Der Stückpreis.
        nummer: Die Projektnummer.

    Returns:
        Die Nummer des Angebots.
    """
    return dateien.dokument_speichern(
        db,
        {"art": "angebot", "nummer": nummer, "kunde_id": 1, "datum": betraege.heute()},
        [{"bezeichnung": "Mischung", "menge": "1", "einheit": "Tag", "preis": preis}],
    )


def _uebersicht(app: object, db: sqlite3.Connection) -> object:
    """Öffnet die Übersicht im Fenster.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.

    Returns:
        Die Seite.
    """
    fenster = Fenster(db)
    fenster.zeige()
    app.processEvents()  # type: ignore[attr-defined]
    fenster.gehe("uebersicht")
    return fenster.seite()


# ------------------------------------------------------------- Die Kacheln


def test_und_die_uebersicht_hat_drei_zahlen(
    app: object, db: sqlite3.Connection
) -> None:
    """Offen, dieses Jahr, Angebote.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    seite = _uebersicht(app, db)

    assert list(seite._gross) == ["offen", "jahr", "angebote"], (
        f"Auf der Übersicht stehen {list(seite._gross)}"
    )


def test_und_offen_zeigt_die_summe_der_offenen_rechnungen(
    app: object, db: sqlite3.Connection
) -> None:
    """Die Zahl, auf die es ankommt.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    _rechnung(db, "100", nummer="0001")
    _rechnung(db, "250", nummer="0002")

    seite = _uebersicht(app, db)

    assert seite._gross["offen"].text() == "350,00 €", (
        f"Auf der Kachel steht {seite._gross['offen'].text()}"
    )
    assert "2 Rechnungen" in seite._klein["offen"].text()


def test_und_wenn_nichts_offen_ist_steht_es_da(
    app: object, db: sqlite3.Connection
) -> None:
    """Nichts offen ist eine Antwort, keine Leere.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    _rechnung(db, "100", bezahlt="01.10.2026")

    seite = _uebersicht(app, db)

    assert seite._gross["offen"].text() == "0,00 €"
    assert "Alles bezahlt" in seite._klein["offen"].text(), (
        f"Darunter steht {seite._klein['offen'].text()!r}"
    )


def test_und_ueberfaellig_steht_nur_wenn_es_wirklich_eins_gibt(
    app: object, db: sqlite3.Connection
) -> None:
    """*Überfällig* ist eine Behauptung. Sie muss stimmen.

    **Damit ist der 1. Januar 2020 als Frist gemeint** — und nicht
    irgendein Datum, das der Vergleich zufällig als abgelaufen hält.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    _rechnung(db, "100", nummer="0001", faellig="01.01.2020")

    seite = _uebersicht(app, db)

    assert "davon überfällig" in seite._klein["offen"].text(), (
        "Eine Rechnung mit Frist 2020 wird nicht als überfällig genannt."
    )
    assert seite._gross["offen"].text() == "100,00 €"


def test_und_keine_zukunftsrechnung_ist_ueberfaellig(
    app: object, db: sqlite3.Connection
) -> None:
    """Eine Frist im nächsten Jahr ist keine abgelaufene.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    _rechnung(db, "100", faellig="31.12.2099")

    seite = _uebersicht(app, db)

    # **Nicht einfach auf das Wort sehen.** Der Satz „1 Rechnung, keine
    # überfällig" enthaelt das Wort auch — dort sagt er aber das
    # Gegenteil. Geprueft wird deshalb auf „davon überfällig", und das
    # steht nur da, wenn es wirklich welche gibt.
    assert "davon überfällig" not in seite._klein["offen"].text()


def test_und_dieses_jahr_zaehlt_nur_rechnungen(
    app: object, db: sqlite3.Connection
) -> None:
    """Ein Angebot ist keine Rechnung und zählt nicht mit.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    _rechnung(db, "100")
    _angebot(db, "900")

    seite = _uebersicht(app, db)

    assert seite._gross["jahr"].text() == "100,00 €", (
        "Ein Angebot steht in der Jahressumme"
    )


def test_und_die_angebote_stehen_fuer_sich(app: object, db: sqlite3.Connection) -> None:
    """Angeboten ohne Rechnung: ein eigener Kasten, kein offener Betrag.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    _angebot(db, "900")

    seite = _uebersicht(app, db)

    assert seite._gross["angebote"].text() == "900,00 €"
    assert seite._gross["offen"].text() == "0,00 €", (
        "Ein Angebot steht als Forderung drin"
    )
    assert "1 Angebot ohne Rechnung" in seite._klein["angebote"].text()


def test_und_ein_abgerechnetes_angebot_steht_nicht_mehr_dort(
    app: object, db: sqlite3.Connection
) -> None:
    """Aus dem Angebot ist ein Vorgang geworden.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    _angebot(db, "900", nummer="0007")
    _rechnung(db, "900", nummer="0007")

    seite = _uebersicht(app, db)

    assert seite._gross["angebote"].text() == "0,00 €", (
        "Ein abgerechnetes Angebot steht noch als offen drin"
    )


# --------------------------------------------------------------- Die Monate


def test_und_die_monatstabelle_hat_zwoelf_zeilen(
    app: object, db: sqlite3.Connection
) -> None:
    """Ein Jahr, nicht dreizehn und nicht elf.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    seite = _uebersicht(app, db)

    assert seite._monats_tabelle.rowCount() == MONATE


def test_und_der_letzte_monat_ist_der_heutige(
    app: object, db: sqlite3.Connection
) -> None:
    """Ganz rechts steht der laufende Monat.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    heute = betraege.lies_datum(betraege.heute())
    assert heute is not None

    seite = _uebersicht(app, db)
    letzter = seite._monats_tabelle.item(MONATE - 1, 0)

    assert letzter is not None
    assert letzter.text() == f"{heute.month:02d}.{str(heute.year)[2:]}", (
        f"Ganz rechts steht {letzter.text()}"
    )


def test_und_die_rechnung_steht_im_richtigen_monat(
    app: object, db: sqlite3.Connection
) -> None:
    """Die Summe steht im Monat ihres Rechnungsdatums.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    _rechnung(db, "100")

    seite = _uebersicht(app, db)
    letzte_zeile = seite._monats_tabelle.item(MONATE - 1, 2)

    assert letzte_zeile is not None
    assert letzte_zeile.text() == "100,00 €", (
        "Die Rechnung steht nicht im laufenden Monat, sondern dort: "
        f"{letzte_zeile.text()}"
    )


def test_und_leere_monate_bleiben_stehen(app: object, db: sqlite3.Connection) -> None:
    """Zwölf Zeilen sind zwölf Zeilen.

    **Kein Verstecken.** Monate ohne Beleg stehen mit 0,00 € da. Wer sie
    nicht sehen will, scannt an ihnen vorbei; eine Lücke im Raster sähe
    nach Datenverlust aus.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    seite = _uebersicht(app, db)

    leer = [
        seite._monats_tabelle.item(zeile, 2).text()  # type: ignore[union-attr]
        for zeile in range(MONATE - 1)
        if seite._monats_tabelle.item(zeile, 2) is not None
    ]

    assert leer == ["0,00 €"] * (MONATE - 1), f"Die leeren Monate zeigen {set(leer)}"


def test_und_die_zahl_stimmt_zur_summe(app: object, db: sqlite3.Connection) -> None:
    """Die Anzahl und die Summe gehören zueinander.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    _rechnung(db, "100", nummer="0001")
    _rechnung(db, "200", nummer="0002")

    seite = _uebersicht(app, db)

    assert seite._monats_tabelle.item(MONATE - 1, 1).text() == "2"  # type: ignore[union-attr]
    assert seite._monats_tabelle.item(MONATE - 1, 2).text() == "300,00 €"  # type: ignore[union-attr]


def test_und_eine_leere_datenbank_zeigt_null(
    app: object, db: sqlite3.Connection
) -> None:
    """Ohne Belege steht überall 0,00 € — und nichts stürzt ab.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    seite = _uebersicht(app, db)

    assert seite._gross["offen"].text() == "0,00 €"
    assert seite._gross["jahr"].text() == "0,00 €"
    assert seite._gross["angebote"].text() == "0,00 €"


# ----------------------------------------------------------- Die Klicks


@pytest.mark.parametrize(
    ("kachel", "bereich"),
    [("offen", "offen"), ("jahr", "dokumente"), ("angebote", "projekte")],
)
def test_und_jede_zahl_fuehrt_wohin_sie_gehoert(
    app: object, db: sqlite3.Connection, kachel: str, bereich: str
) -> None:
    """Eine Zahl, die man nur ablesen kann, ist ein Bildschirmmuster.

    Gesucht wird die Taste **über ihren Namen**, nicht über ihren Text —
    sonst wäre der Test eine zweite Wahrheit über die Beschriftung.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
        kachel: Der Bereich, zu dem die Kachel zeigen muss.
        bereich: Derselbe Bereich — er steht am Namen der Taste.
    """
    from PySide6.QtWidgets import QPushButton

    fenster = Fenster(db)
    fenster.zeige()
    app.processEvents()  # type: ignore[attr-defined]
    fenster.gehe("uebersicht")

    gesucht = [
        k
        for k in fenster.seite().findChildren(QPushButton)
        if k.objectName() == f"kachel_{bereich}"
    ]
    assert gesucht, f"Die Kachel *{kachel}* hat keine Taste nach *{bereich}*"

    gesucht[0].click()
    app.processEvents()  # type: ignore[attr-defined]

    assert fenster.seite() is fenster.seiten[bereich], (
        f"Die Kachel *{kachel}* fuehrt nicht zu *{bereich}*"
    )
    fenster.fenster.close()


def test_und_keine_kachel_fuehrt_ins_leere() -> None:
    """Jeder Bereich, zu dem eine Kachel führt, gibt es wirklich.

    Sonst wäre die Taste ein Weg ins Nichts — und still.

    Returns:
        Nichts.
    """
    vorhanden = {schluessel for schluessel, _t, _k in BEREICHE}

    for ziel in ("offen", "dokumente", "projekte"):
        assert ziel in vorhanden, (
            f"Die Übersicht zeigt einen Weg zu *{ziel}*, den es nicht gibt"
        )
