"""Das Datum, das in der Liste steht.

Bis hierher stand in der Dokumentenliste ``26..2..1`` statt ``06.10.``.
Gespeichert wird als ``TT.MM.JJJJ`` — :func:`faktur.betraege.datum`
normalisiert darauf —, geschnitten wurde aber nach ``JJJJ-MM-TT``.

**Warum das so lange nobody aufgefallen ist:** Die Liste war auf einer
frischen Datenbank leer, und ein Leerlauf zeigt keinen Fehler. Sobald ein
Beleg drinstand, stand die kaputte Zahl da. Bei 0.9.0 gab es den Fenster-
umbau, der Dokumentenliste neu schrieb — und beim Umschreiben kam der
Fehler mit hinein.

Darum steht hier eine Tabelle mit echten Daten, und jede Zeile vergleicht,
**was gespeichert** ist mit **was angezeigt** wird. Nicht die Funktion,
sondern ihr Ergebnis: Ein Test, der nach einem ``[8:10]`` im Quelltext
sucht, sagt nichts mehr, sobald der Schnitt stimmt.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

from faktur import betraege, dateien  # noqa: E402

#: Ein Datum, an dem man den Fehler sofort sieht.
#:
#: Nach ``JJJJ-MM-TT`` geschnitten käme ``26..2..1`` heraus.
#: Richtig ist ``06.10.``
DATUM = "06.10.2026"
KURZ = "06.10."


# ----------------------------------------- was wirklich auf der Platte liegt


def test_und_das_gespeicherte_datum_ist_so_lesbar(tmp_path: object) -> None:
    """Zuerst die Voraussetzung: So liegt es auf der Platte.

    Stimmt das hier nicht, ist jeder Fehler darunter schon richtig.

    Args:
        tmp_path: Das temporäre Verzeichnis.
    """
    from faktur import db as datenbank

    verbindung = datenbank.verbinden(tmp_path / "datum.db")
    kunde = dateien.kunde_speichern(verbindung, {"firma": "Soundcheck GmbH"})
    nummer = dateien.dokument_speichern(
        verbindung,
        {"art": "angebot", "nummer": "0199", "kunde_id": kunde, "datum": DATUM},
        [{"bezeichnung": "Ton", "menge": "2", "einheit": "Tag", "preis": "100"}],
    )

    gespeichert = dateien.dokument_holen(verbindung, nummer)["datum"]

    assert gespeichert == DATUM, f"Auf der Platte liegt {gespeichert!r}"
    assert betraege.datum(DATUM) == DATUM, "beträge normalisiert anders"


@pytest.mark.parametrize(
    ("gegeben", "erwartet"),
    [
        ("06.10.2026", "06.10.2026"),
        ("1.2.2027", "01.02.2027"),
        ("2026-10-06", "06.10.2026"),
        ("06/10/2026", "06.10.2026"),
    ],
)
def test_und_eingaben_werden_alle_gleich_geschrieben(
    gegeben: str, erwartet: str
) -> None:
    """Vier Schreibweisen, ein Datum.

    Wer ``2026-10-06`` eintippt, bekommt dasselbe gespeichert wie bei
    ``06.10.2026`` — und sieht danach überall dasselbe stehen.

    Args:
        gegeben: Was eingegeben wurde.
        erwartet: Was daraufhin in der Datenbank liegt.
    """
    assert betraege.datum(gegeben) == erwartet


# -------------------------------------------------- was die Liste anzeigt


@pytest.mark.parametrize(
    ("gespeichert", "erwartet"),
    [
        ("06.10.2026", "06.10."),
        ("31.12.2026", "31.12."),
        ("01.02.2027", "01.02."),
        ("", ""),
        ("kein Datum", ""),
    ],
)
def test_und_die_liste_zeigt_das_datum_richtig_herum(
    gespeichert: str, erwartet: str
) -> None:
    """Was gespeichert ist, steht auch da — richtig herum gekürzt.

    Args:
        gespeichert: Was in der Datenbank liegt.
        erwartet: Was in der Liste stehen soll.
    """
    from faktur.gui.listen import kurz_datum

    assert kurz_datum(gespeichert) == erwartet, (
        f"Aus {gespeichert!r} wurde {kurz_datum(gespeichert)!r} statt {erwartet!r}"
    )


def test_und_das_ist_auch_in_der_echten_liste_so(tmp_path: object) -> None:
    """Nicht die Funktion, sondern das Fenster.

    Ein Fehler, der in einer Zeile steckt, kann sich in der Tabelle wieder
    verstecken — dann stimmt die Funktion und das Bildschirmfoto nicht.

    Args:
        tmp_path: Das temporäre Verzeichnis.
    """
    from faktur import db as datenbank
    from faktur.gui.fenster import Fenster
    from PySide6.QtWidgets import QApplication

    verbindung = datenbank.verbinden(tmp_path / "liste.db")
    kunde = dateien.kunde_speichern(verbindung, {"firma": "Soundcheck GmbH"})
    dateien.dokument_speichern(
        verbindung,
        {"art": "angebot", "nummer": "0199", "kunde_id": kunde, "datum": DATUM},
        [{"bezeichnung": "Ton", "menge": "2", "einheit": "Tag", "preis": "100"}],
    )

    laufend = QApplication.instance() or QApplication([])
    fenster = Fenster(verbindung)
    fenster.zeige()
    laufend.processEvents()
    fenster.gehe("dokumente")

    modell = fenster.seite().ansicht.model()
    zeile = modell.zellen(modell.datensatz(0))

    assert zeile[1] == KURZ, f"In der Dokumentenliste steht {zeile[1]!r}"
    fenster.fenster.close()
