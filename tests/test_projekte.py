"""Die Projekte, und was rechts daneben steht.

**Ein Projekt ist ein Kunde und eine Nummer.** Angebot 0199 und Rechnung
0199 sind ein Vorgang, nicht zwei — und genau daran hat es bisher keine
Stelle gegeben. Es gab eine Dokumentenliste, in der beide als zwei
verschiedene Sachen standen.

Hier steht beides nebeneinander. Diese Datei prüft zwei getrennte Dinge:

- :func:`faktur.dateien.projekte` rechnet richtig — ohne Fenster, ohne
  Qt, damit ein Fehler in der Rechnung an einer Stelle steht.
- :class:`faktur.gui.projekte.ProjekteSeite` zeigt es richtig an.

**Die Zahlen meinen nicht dasselbe.** *Summe* ist das, was berechnet
wurde, und wo noch nichts berechnet wurde, das Angebot. *Offen* ist der
Betrag, auf den noch Geld fehlt, und da zählt nur die Rechnung hinein.
Beide Zahlen falsch lesen ist teurer, als sie wegzulassen — deshalb
stehen beide da und beide haben ihren eigenen Test.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

from faktur import dateien  # noqa: E402


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
    """Legt eine frische Datenbank an.

    Args:
        tmp_path: Das temporäre Verzeichnis.

    Returns:
        Die offene Verbindung.
    """
    from faktur import db as datenbank

    verbindung = datenbank.verbinden(tmp_path / "projekte.db")
    dateien.kunde_speichern(verbindung, {"firma": "Soundcheck GmbH"})
    dateien.kunde_speichern(verbindung, {"firma": "Zeta Tonwerk"})
    return verbindung


def _kunde(db: sqlite3.Connection, firma: str) -> int:
    """Gibt die Nummer eines angelegten Kunden zurück.

    Args:
        db: Die Datenbankverbindung.
        firma: Der Name der Firma.

    Returns:
        Die Nummer des Kunden.
    """
    zeile = db.execute("SELECT id FROM kunden WHERE firma = ?", (firma,)).fetchone()
    assert zeile is not None, f"{firma} ist nicht angelegt"
    return int(zeile["id"])


def _beleg(
    db: sqlite3.Connection,
    firma: str,
    art: str,
    nummer: str = "0199",
    datum: str = "06.10.2026",
    preis: str = "100",
    menge: str = "1",
    bezahlt: str = "",
    faellig: str = "",
    gueltig: str = "",
) -> int:
    """Legt einen Beleg an.

    Args:
        db: Die Datenbankverbindung.
        firma: Der Name des Kunden.
        art: Angebot oder Rechnung.
        nummer: Die Projektnummer.
        datum: Das Datum des Belegs.
        preis: Der Stückpreis.
        menge: Die Menge.
        bezahlt: Das Zahlungsdatum, leer für offen.
        faellig: Das Fälligkeitsdatum.
        gueltig: Das Ablaufdatum eines Angebots.

    Returns:
        Die Nummer des Belegs.
    """
    return dateien.dokument_speichern(
        db,
        {
            "art": art,
            "nummer": nummer,
            "kunde_id": _kunde(db, firma),
            "datum": datum,
            "faellig": faellig,
            "gueltig_bis": gueltig,
            "bezahlt_am": bezahlt,
        },
        [
            {
                "bezeichnung": "Aufnahme Ton",
                "menge": menge,
                "einheit": "Tag",
                "preis": preis,
            }
        ],
    )


#: Eine Verbindung mit einem Beleg, fuer die Reihenfolgepruefungen unten.
_VERBINDUNGUNG: sqlite3.Connection | None = None

#: Der Beleg aus derselben Verbindung.
_EIN_BELEG: sqlite3.Row | None = None


def _eine_verbindung_mit_beleg() -> None:
    """Legt eine Verbindung mit genau einem Beleg an.

    Returns:
        Nichts.
    """
    global _VERBINDUNGUNG, _EIN_BELEG  # noqa: PLW0603

    import tempfile

    from faktur import db as datenbank

    _VERBINDUNGUNG = datenbank.verbinden(Path(tempfile.mkdtemp()) / "geld.db")
    kunde = dateien.kunde_speichern(_VERBINDUNGUNG, {"firma": "Soundcheck GmbH"})
    nummer = dateien.dokument_speichern(
        _VERBINDUNGUNG,
        {"art": "rechnung", "nummer": "0199", "kunde_id": kunde, "datum": "06.10.2026"},
        [{"bezeichnung": "Ton", "menge": "2", "einheit": "Tag", "preis": "850"}],
    )
    _EIN_BELEG = dateien.dokument_holen(_VERBINDUNGUNG, nummer)


_eine_verbindung_mit_beleg()


# --------------------------------------------------------- Die Rechnung


def test_und_ein_angebot_allein_ist_schon_ein_projekt(db: sqlite3.Connection) -> None:
    """Ein Angebot ohne Rechnung ist ein Projekt mit offenem Ende.

    Args:
        db: The Datenbankverbindung.
    """
    _beleg(db, "Soundcheck GmbH", "angebot")

    projekte = dateien.projekte(db)

    assert len(projekte) == 1, f"Es gibt {len(projekte)} Projekte"
    assert projekte[0]["nummer"] == "0199"
    assert projekte[0]["firma"] == "Soundcheck GmbH"


def test_und_angebot_und_rechnung_sind_ein_projekt(db: sqlite3.Connection) -> None:
    """Zwei Belege, eine Nummer: ein Vorgang.

    Args:
        db: The Datenbankverbindung.
    """
    _beleg(db, "Soundcheck GmbH", "angebot")
    _beleg(db, "Soundcheck GmbH", "rechnung", datum="20.10.2026")

    projekte = dateien.projekte(db)

    assert len(projekte) == 1, "Angebot und Rechnung wurden getrennt gezählt"
    assert projekte[0]["angebote"] == 1
    assert projekte[0]["rechnungen"] == 1


def test_und_gleiche_nummer_bei_zwei_kunden_ist_zwei_projekte(
    db: sqlite3.Connection,
) -> None:
    """Die Nummer allein macht das Projekt nicht aus.

    Sonst hinge beim Kundenwechsel der Vorgang des einen an dem des
    anderen, und die Summe wäre die Summe zweier Fremder.

    Args:
        db: The Datenbankverbindung.
    """
    _beleg(db, "Soundcheck GmbH", "angebot")
    _beleg(db, "Zeta Tonwerk", "angebot")

    projekte = dateien.projekte(db)

    assert len(projekte) == 2, "Zwei Kunden wurden zu einem Projekt gemacht"
    assert {p["firma"] for p in projekte} == {"Soundcheck GmbH", "Zeta Tonwerk"}


def test_und_ohne_kunde_gibt_es_keinen_sturz(db: sqlite3.Connection) -> None:
    """Ein Beleg ohne Kunde darf die Liste nicht umwerfen.

    Args:
        db: The Datenbankverbindung.
    """
    dateien.dokument_speichern(
        db,
        {"art": "angebot", "nummer": "0777", "kunde_id": None, "datum": "06.10.2026"},
        [{"bezeichnung": "Ton", "menge": "1", "einheit": "Tag", "preis": "10"}],
    )

    projekte = dateien.projekte(db)

    assert len(projekte) == 1, "Ein Beleg ohne Kunde ist kein Projekt"
    assert projekte[0]["firma"] == "(kein Kunde)"
    assert dateien.projekt_belege(db, projekte[0]) == []


# ------------------------------------------------------------ Die Zahlen


def test_und_wo_nichts_berechnet_wurde_steht_das_angebot(
    db: sqlite3.Connection,
) -> None:
    """Ohne Rechnung ist das Angebot der Wert des Projekts.

    Args:
        db: The Datenbankverbindung.
    """
    _beleg(db, "Soundcheck GmbH", "angebot", preis="850")

    projekt = dateien.projekte(db)[0]

    assert dateien.projektsumme(projekt) == 850.0, (
        "Die Summe eines noch nicht abgerechneten Projekts ist die des Angebots"
    )


def test_und_nach_dem_ablechnen_zaehlt_die_rechnung(db: sqlite3.Connection) -> None:
    """Die Rechnung schlägt das Angebot.

    Sonst stünde nach dem Abrechnen eine andere Zahl in der Liste als
    vorher, ohne dass sich am Projekt etwas geändert hätte — nur weil ein
    zweites Dokument dazugekommen ist.

    Args:
        db: The Datenbankverbindung.
    """
    _beleg(db, "Soundcheck GmbH", "angebot", preis="850")
    _beleg(db, "Soundcheck GmbH", "rechnung", datum="20.10.2026", preis="700")

    projekt = dateien.projekte(db)[0]

    assert dateien.projektsumme(projekt) == 700.0, (
        "Nach dem Abrechnen muss die Rechnung gelten, nicht das Angebot"
    )


def test_und_die_summe_ist_menge_mal_preis(db: sqlite3.Connection) -> None:
    """Zwei Tage zu 850 sind 1700.

    Args:
        db: The Datenbankverbindung.
    """
    _beleg(db, "Soundcheck GmbH", "rechnung", preis="850", menge="2")

    projekt = dateien.projekte(db)[0]

    assert dateien.projektsumme(projekt) == 1700.0


def test_und_ein_angebot_schuldet_niemandem_geld(db: sqlite3.Connection) -> None:
    """*Offen* zählt nur Rechnungen hinein.

    Ein Angebot ist eine Absichtserklärung. Trüge sie in *offen* ein,
    stünde da ein Betrag, den niemand schuldet.

    Args:
        db: The Datenbankverbindung.
    """
    _beleg(db, "Soundcheck GmbH", "angebot", preis="850")

    projekt = dateien.projekte(db)[0]

    assert float(projekt["offen"]) == 0.0, "Ein Angebot steht als Forderung drin"
    assert dateien.projektstand(projekt) == "angeboten"


def test_und_eine_offene_rechnung_steht_als_offen(db: sqlite3.Connection) -> None:
    """Nicht gezahlt heißt offen.

    Args:
        db: The Datenbankverbindung.
    """
    _beleg(db, "Soundcheck GmbH", "rechnung", preis="850", faellig="05.11.2026")

    projekt = dateien.projekte(db)[0]

    assert float(projekt["offen"]) == 850.0
    assert dateien.projektstand(projekt) == "offen"


def test_und_eine_bezahlte_rechnung_steht_als_bezahlt(db: sqlite3.Connection) -> None:
    """Bezahlt heißt bezahlt — auch wenn das Datum lange her ist.

    Args:
        db: The Datenbankverbindung.
    """
    _beleg(
        db,
        "Soundcheck GmbH",
        "rechnung",
        preis="850",
        bezahlt="01.11.2026",
        faellig="05.11.2026",
    )

    projekt = dateien.projekte(db)[0]

    assert float(projekt["offen"]) == 0.0, "Eine bezahlte Rechnung steht als offen"
    assert dateien.projektstand(projekt) == "bezahlt"


def test_und_eine_rechnung_ueber_der_frist_steht_als_ueberfaellig(
    db: sqlite3.Connection,
) -> None:
    """Überfellig ist offen, nur dringender.

    Args:
        db: The Datenbankverbindung.
    """
    _beleg(db, "Soundcheck GmbH", "rechnung", preis="850", faellig="01.01.2020")

    assert dateien.projektstand(dateien.projekte(db)[0]) == "überfällig"


def test_und_ein_abgelaufenes_angebot_steht_als_abgelaufen(
    db: sqlite3.Connection,
) -> None:
    """Ein Angebot hat ein Ablaufdatum, und danach ist es vorbei.

    Args:
        db: The Datenbankverbindung.
    """
    _beleg(db, "Soundcheck GmbH", "angebot", gueltig="01.01.2020")

    assert dateien.projektstand(dateien.projekte(db)[0]) == "abgelaufen"


def test_und_eine_rechnung_macht_aus_einem_abgelaufenen_angebot_kein_abgelaufenes(
    db: sqlite3.Connection,
) -> None:
    """Wer abgerechnet hat, ist nicht abgelaufen.

    Args:
        db: The Datenbankverbindung.
    """
    _beleg(db, "Soundcheck GmbH", "angebot", gueltig="01.01.2020")
    _beleg(db, "Soundcheck GmbH", "rechnung", datum="20.10.2026", preis="850")

    assert dateien.projektstand(dateien.projekte(db)[0]) == "offen"


# ----------------------------------------------------------- Die Belege


def test_und_die_belege_kommen_zeitlich_richtig(db: sqlite3.Connection) -> None:
    """Das Angebot zuerst, weil es das frühere ist.

    Args:
        db: The Datenbankverbindung.
    """
    _beleg(db, "Soundcheck GmbH", "angebot", datum="06.10.2026")
    _beleg(db, "Soundcheck GmbH", "rechnung", datum="20.10.2026")

    belege = dateien.projekt_belege(db, dateien.projekte(db)[0])

    assert [b["art"] for b in belege] == ["angebot", "rechnung"]


def test_und_es_kommen_nur_die_belege_dieses_projekts(db: sqlite3.Connection) -> None:
    """Der Kunde hat zwei Projekte; hier steht nur eins davon.

    Args:
        db: The Datenbankverbindung.
    """
    _beleg(db, "Soundcheck GmbH", "angebot", nummer="0199")
    _beleg(db, "Soundcheck GmbH", "rechnung", nummer="0199", datum="20.10.2026")
    _beleg(db, "Soundcheck GmbH", "angebot", nummer="0200", datum="01.10.2026")

    projekt = next(p for p in dateien.projekte(db) if p["nummer"] == "0199")
    belege = dateien.projekt_belege(db, projekt)

    assert len(belege) == 2, f"Es kamen {len(belege)} Belege"
    assert {b["nummer"] for b in belege} == {"0199"}


# ------------------------------------------------------ Die Seite im Fenster


def test_und_die_seite_zeigt_projekte_und_belege_nebeneinander(
    app: object, db: sqlite3.Connection
) -> None:
    """Links das Projekt, rechts sein Beleg.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    from faktur.gui.fenster import Fenster

    _beleg(db, "Soundcheck GmbH", "angebot")
    _beleg(db, "Soundcheck GmbH", "rechnung", datum="20.10.2026")
    _beleg(db, "Zeta Tonwerk", "angebot", nummer="0200", datum="01.10.2026")

    fenster = Fenster(db)
    fenster.zeige()
    app.processEvents()  # type: ignore[attr-defined]
    fenster.gehe("projekte")
    seite = fenster.seite()

    assert seite.projekte.model().rowCount() == 2, "Es stehen nicht zwei Projekte da"
    assert seite.belege.model().rowCount() == 3, "Ohne Auswahl fehlen Belege"
    fenster.fenster.close()


def test_und_ein_projekt_zeigt_seine_belege(
    app: object, db: sqlite3.Connection
) -> None:
    """Markiert man links ein Projekt, stehen rechts nur seine Belege.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    from faktur.gui.fenster import Fenster

    _beleg(db, "Soundcheck GmbH", "angebot")
    _beleg(db, "Soundcheck GmbH", "rechnung", datum="20.10.2026")
    _beleg(db, "Zeta Tonwerk", "angebot", nummer="0200", datum="01.10.2026")

    fenster = Fenster(db)
    fenster.zeige()
    app.processEvents()  # type: ignore[attr-defined]
    fenster.gehe("projekte")
    seite = fenster.seite()

    zeile = next(
        n
        for n in range(seite.projekte.model().rowCount())
        if seite.projekte.model().zellen(seite.projekte.model().datensatz(n))[0]
        == "Soundcheck GmbH"
    )
    seite.projekte.setCurrentIndex(seite.projekte.model().index(zeile, 0))

    assert seite.belege.model().rowCount() == 2, (
        "Rechts stehen nicht die zwei Belege des Projekts"
    )
    assert "0199" in seite.ueberschrift_belege.text()
    fenster.fenster.close()


def test_und_ohne_projekt_stehen_alle_belege_da(
    app: object, db: sqlite3.Connection
) -> None:
    """Wer nichts markiert, sieht alles.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    from faktur.gui.fenster import Fenster

    _beleg(db, "Soundcheck GmbH", "angebot")
    _beleg(db, "Zeta Tonwerk", "angebot", nummer="0200", datum="01.10.2026")

    fenster = Fenster(db)
    fenster.zeige()
    app.processEvents()  # type: ignore[attr-defined]
    fenster.gehe("projekte")
    seite = fenster.seite()

    assert seite.belege.model().rowCount() == 2
    assert "Alle Belege" in seite.ueberschrift_belege.text()
    fenster.fenster.close()


def test_und_eine_leere_datenbank_sagt_es(app: object, db: sqlite3.Connection) -> None:
    """Eine leere Seite ohne einen Wort sieht nach kaputtem Programm aus.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    from faktur.gui.fenster import Fenster

    fenster = Fenster(db)
    fenster.zeige()
    app.processEvents()  # type: ignore[attr-defined]
    fenster.gehe("projekte")
    seite = fenster.seite()

    assert seite.projekte.model().rowCount() == 0
    assert seite._leer.isVisible(), "Es steht kein Wort auf der leeren Seite"
    fenster.fenster.close()


def test_und_doppelklick_oeffnet_den_beleg(app: object, db: sqlite3.Connection) -> None:
    """Rechts anklicken, doppelt: der Beleg geht auf.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    from faktur.gui.editor import EditorFenster
    from faktur.gui.fenster import Fenster

    _beleg(db, "Soundcheck GmbH", "angebot")

    fenster = Fenster(db)
    fenster.zeige()
    app.processEvents()  # type: ignore[attr-defined]
    fenster.gehe("projekte")
    seite = fenster.seite()

    vorher = [
        w for w in offene_fenster() if isinstance(w, EditorFenster) and w.isVisible()
    ]
    seite.belege.doubleClicked.emit(seite.belege.model().index(0, 0))

    nachher = [
        w for w in offene_fenster() if isinstance(w, EditorFenster) and w.isVisible()
    ]
    assert len(nachher) == len(vorher) + 1, "Der Beleg ging nicht auf"

    for w in nachher:
        w.close()
    fenster.fenster.close()


def offene_fenster() -> list[object]:
    """Gibt alle offenen Fenster zurück.

    Returns:
        Die Fenster.
    """
    from PySide6.QtWidgets import QApplication

    laufend = QApplication.instance()
    return laufend.topLevelWidgets() if laufend else []


def test_und_die_suche_zeigt_nur_diese_projekte(
    app: object, db: sqlite3.Connection
) -> None:
    """Gesucht wird in den Projekten.

    Args:
        app: Die Qt-Anwendung.
        db: Die Datenbankverbindung.
    """
    from faktur.gui.fenster import Fenster

    _beleg(db, "Soundcheck GmbH", "angebot")
    _beleg(db, "Zeta Tonwerk", "angebot", nummer="0200")

    fenster = Fenster(db)
    fenster.zeige()
    app.processEvents()  # type: ignore[attr-defined]
    fenster.gehe("projekte")
    seite = fenster.seite()

    seite.begriff = "zeta"
    seite.fuelle("zeta")

    assert seite.projekte.model().rowCount() == 1, "Die Suche greift nicht"
    zellen = seite.projekte.model().zellen(seite.projekte.model().datensatz(0))
    assert zellen[0] == "Zeta Tonwerk"
    fenster.fenster.close()


def test_und_die_spalten_sind_nicht_doppelt() -> None:
    """Zwei gleichnamige Spalten sind unlesbar.

    Returns:
        Nichts.
    """
    from faktur.gui.projekte import SPALTEN

    assert len(SPALTEN) == len(set(SPALTEN)), f"Doppelte Spalten in {SPALTEN}"


def test_und_die_projektliste_bleibt_schmal() -> None:
    """**Vier Spalten, nicht mehr.**

    Links steht nicht mal die halbe Fensterbreite. Bei sechs Spalten war
    der Kunde auf *Soundc…* zusammengeschoben, und an einem
    abgeschnittenen Kunden erkennt man den Vorgang nicht.

    **Die Geldsummen stehen trotzdem nirgends verloren.** Sie stehen
    rechts an jedem einzelnen Beleg — was genauer ist als eine Summe in
    der Projektliste, und doppelt waere es nur.

    Returns:
        Nichts.
    """
    from faktur.gui.projekte import SPALTEN

    assert len(SPALTEN) == 4, f"Die Projektliste hat {len(SPALTEN)} Spalten"
    assert SPALTEN == ("Kunde", "Nr.", "vom", "Stand"), f"Sie heisst {SPALTEN}"


def test_und_kein_beleg_zeigt_ohne_geldsumme() -> None:
    """Jeder Beleg rechts nennt seinen Betrag.

    Weil die Projektliste keine Geldsumme mehr hat, muss sie rechts
    stehen — sonst wäre beim Wegnehmen der Spalten Geld verloren
    gegangen, und niemand hätte es gemerkt.

    Returns:
        Nichts.
    """
    from faktur.gui.listen import dokument_zellen

    spalten = ("Nummer", "Datum", "Kunde", "Art", "Summe", "Status")

    zeile = dokument_zellen(_VERBINDUNGUNG)(_EIN_BELEG)

    assert len(zeile) == len(spalten), "Die Zeile passt nicht zu den Spalten"
    assert zeile[4].endswith("€"), (
        f"Die Geldsumme steht nicht an vierter Stelle: {zeile}"
    )
    assert zeile[4] == "1.700,00 €", f"Die Geldsumme stimmt nicht: {zeile[4]}"
