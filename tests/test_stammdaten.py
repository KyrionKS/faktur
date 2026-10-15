"""Die Stammdatenseite und der Hinweis auf der Übersicht.

Es geht um zwei Dinge, die beide mit **Finden** zu tun haben.

Erstens: Bis hierher lagen die Stammdaten hinter *Einstellungen…* im
Menü, und auf dem Mac waren sie dort nicht zu finden — Qt schiebt einen
Punkt mit dieser Rolle ins Programm-Menü, und das hieß noch *Python*.
Man konnte etwas eingeben und kam nicht dazu. Die Seite ist darum in die
Seitenleiste gewandert.

Zweitens: Ein frisches Programm kennt weder Firmenname noch IBAN, und
sagt nichts. Die PDF kommen trotzdem heraus, nur ohne Absender. Genau
darum fragt die Übersicht jetzt nach.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

from faktur import db, einstellungen  # noqa: E402
from faktur.gui.fenster import BEREICHE, Fenster  # noqa: E402
from faktur.gui.stammdaten import StammdatenSeite  # noqa: E402
from faktur.gui.uebersicht import UebersichtSeite  # noqa: E402


@pytest.fixture
def app() -> object:
    """Gibt die laufende Qt-Anwendung zurück.

    Returns:
        Die Anwendung.
    """
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def fenster(app: object, tmp_path: Path) -> Fenster:
    """Baut ein Fenster mit einer frischen Datenbank.

    Returns:
        Das Fenster.
    """
    test = Fenster(db.verbinden(tmp_path / "stammdaten.db"))
    test.zeige()
    app.processEvents()  # type: ignore[attr-defined]
    return test


# --------------------------------------------------------------- Auffindbar


def test_die_stammdaten_stehen_in_der_seitenleiste() -> None:
    """Sie stehen in der Leiste, nicht nur im Menü.

    Das ist der ganze Punkt: Ein Menüpunkt mit der Rolle *Einstellungen*
    wandert auf dem Mac ins Programm-Menü, und das hieß lange *Python*.

    Args:
        None
    """
    schluessel = [schluessel for schluessel, _t, _k in BEREICHE]

    assert "stammdaten" in schluessel, (
        f"Die Stammdaten stehen nicht in der Seitenleiste. Dort stehen {schluessel}."
    )


def test_und_als_seite_nicht_als_blatt(fenster: Fenster) -> None:
    """Die Seite ist eine Seite — sie liegt im Stapel und ist benannt.

    Args:
        fenster: Das Fenster.
    """
    seite = fenster.seiten["stammdaten"]

    assert isinstance(seite, StammdatenSeite)
    assert seite.isWidgetType(), "Die Stammdaten sind kein Fenster mehr"

    fenster.gehe("stammdaten")
    assert seite.isVisible()
    assert fenster.buehne.currentIndex() == fenster.reihenfolge.index("stammdaten")


def test_und_der_kurzbefehl_springt_hin(fenster: Fenster) -> None:
    """Cmd+, geht dorthin, wo man die Daten auch ohne Menü findet.

    Args:
        fenster: Das Fenster.
    """
    kuerzel = {schluessel: kuerzel for schluessel, _t, kuerzel in BEREICHE}
    assert kuerzel["stammdaten"] == "Ctrl+7", (
        f"Der siebte Bereich hört auf {kuerzel['stammdaten']}."
    )

    fenster.gehe("kunden")
    fenster.gehe("stammdaten")
    assert fenster.seite() is fenster.seiten["stammdaten"]


# ------------------------------------------------------------- Speichern


def test_und_die_seite_speichert_ihre_werte(fenster: Fenster) -> None:
    """Was getippt wurde, steht danach in der Datenbank.

    Args:
        fenster: Das Fenster.
    """
    seite = fenster.seiten["stammdaten"]
    seite.felder["firma"].setText("New Air Media Group")
    seite.felder["iban"].setText("DE02 1203 0000 0000 2020 51")
    seite.felder["steuernummer"].setText("123/456/789")

    assert seite.speichern() is True

    assert einstellungen.hole(fenster.db, "firma") == "New Air Media Group"
    assert einstellungen.hole(fenster.db, "iban") == "DE02 1203 0000 0000 2020 51"
    assert einstellungen.hole(fenster.db, "steuernummer") == "123/456/789"


def test_und_die_bausteine_werden_ebenfalls_gespeichert(fenster: Fenster) -> None:
    """Der Brieftext auf dem Angebot ist nicht weniger wichtig als die IBAN.

    Args:
        fenster: Das Fenster.
    """
    seite = fenster.seiten["stammdaten"]
    seite.bausteine["text_angebot"].setPlainText(
        "Hallo {{Kunde_Anrede}},\n\nviel Erfolg"
    )

    seite.speichern()

    assert einstellungen.baustein(fenster.db, "angebot").startswith("Hallo")


def test_und_was_nicht_gespeichert_wurde_bleibt_stehen(fenster: Fenster) -> None:
    """Nach dem Neuladen steht das Gespeicherte im Feld, nicht das Leere.

    Args:
        fenster: Das Fenster.
    """
    seite = fenster.seiten["stammdaten"]
    seite.felder["firma"].setText("Tonstudio Nordwind")
    seite.speichern()

    seite.erneut_laden()

    assert seite.felder["firma"].text() == "Tonstudio Nordwind"


def test_die_seite_hat_alle_felder_die_es_gibt(fenster: Fenster) -> None:
    """Jedes Feld aus der Datenbank hat auch ein Feld auf der Seite.

    Args:
        fenster: Das Fenster.
    """
    seite = fenster.seiten["stammdaten"]

    for schluessel, beschriftung in einstellungen.FELDER:
        assert schluessel in seite.felder, (
            f"Für „{beschriftung}“ ({schluessel}) gibt es kein Feld."
        )

    for schluessel in einstellungen.BAUSTEINE_VORSCHLAG:
        assert schluessel in seite.bausteine, (
            f"Für den Baustein {schluessel} gibt es kein Feld."
        )


# --------------------------------------------------------------- Der Hinweis


def test_die_uebersicht_zeigt_fehlende_stammdaten(fenster: Fenster) -> None:
    """Eine frische Installation hat keine Daten — und sagt es.

    Args:
        fenster: Das Fenster.
    """
    seite = fenster.seiten["uebersicht"]
    seite.beim_zeigen()

    assert isinstance(seite, UebersichtSeite)
    assert not einstellungen.vollstaendig(fenster.db)
    assert seite.hinweis.isVisible(), (
        "Der Hinweis bleibt weg, obwohl Firma und IBAN fehlen. Die PDF "
        "kommen dann ohne Absender heraus."
    )


def test_und_verschwindet_nach_dem_ausfuellen(fenster: Fenster) -> None:
    """Wer alles eingetragen hat, wird nicht mehr darauf hingewiesen.

    Args:
        fenster: Das Fenster.
    """
    stammen = fenster.seiten["stammdaten"]
    stammen.felder["firma"].setText("New Air Media Group")
    stammen.felder["iban"].setText("DE02 1203 0000 0000 2020 51")
    stammen.speichern()

    uebersicht = fenster.seiten["uebersicht"]
    uebersicht.beim_zeigen()

    assert einstellungen.vollstaendig(fenster.db)
    assert not uebersicht.hinweis.isVisible(), "Der Hinweis bleibt trotz allem stehen"


def test_und_der_hinweis_fuehrt_selbst_waeg(fenster: Fenster) -> None:
    """Die Taste im Hinweis springt zu den Stammdaten.

    Args:
        fenster: Das Fenster.
    """
    fenster.gehe("kunden")
    uebersicht = fenster.seiten["uebersicht"]
    uebersicht.beim_zeigen()

    uebersicht._stammdaten_geoeffnet()

    assert fenster.seite() is fenster.seiten["stammdaten"]


def test_und_der_hinweis_kommt_wieder_wenn_etwas_geloescht_wird(
    fenster: Fenster,
) -> None:
    """Wer die IBAN wieder loescht, sieht den Hinweis wieder.

    Args:
        fenster: Das Fenster.
    """
    stammen = fenster.seiten["stammdaten"]
    stammen.felder["firma"].setText("New Air Media Group")
    stammen.felder["iban"].setText("DE02 1203 0000 0000 2020 51")
    stammen.speichern()

    uebersicht = fenster.seiten["uebersicht"]
    uebersicht.beim_zeigen()
    assert not uebersicht.hinweis.isVisible()

    einstellungen.speichere(fenster.db, "iban", "")
    uebersicht.beim_zeigen()

    assert uebersicht.hinweis.isVisible()


def test_und_kein_dialog_mehr_fuer_die_einstellungen() -> None:
    """Es gibt nur noch eine Stelle, an der die Stammdaten stehen.

    Zwei Orte wären zwei Wahrheiten: Man ändert sie an einem und wundert
    sich über den anderen.

    Args:
        None
    """
    quelle = Path(__file__).resolve().parents[1] / "faktur" / "gui" / "fenster.py"
    text = quelle.read_text(encoding="utf-8")

    assert "StammdatenDialog" not in text, (
        "Das Fenster oeffnet noch ein Blatt mit den Stammdaten. Es gibt "
        "jetzt eine Seite."
    )
    assert 'lambda: self.gehe("stammdaten")' in text, (
        "Cmd+, springt nicht auf die Seite."
    )


def test_und_es_gibt_keinen_dokumentenordner_mehr() -> None:
    """Der Menüpunkt zeigt auf einen Ordner, in dem nichts mehr landet.

    Args:
        None
    """
    text = (
        Path(__file__).resolve().parents[1] / "faktur" / "gui" / "fenster.py"
    ).read_text(encoding="utf-8")

    assert "Dokumentenordner" not in text, (
        "Der Punkt steht noch da. Die PDF waehlt jetzt der Benutzer."
    )


def test_die_testdatenbank_bleibt_bei_den_tests(tmp_path: Path) -> None:
    """Die Seite schreibt dorthin, wohin ihre Verbindung zeigt.

    Args:
        tmp_path: Das temporaere Verzeichnis.
    """
    verbindung = db.verbinden(tmp_path / "wegweiser.db")
    seite = StammdatenSeite(verbindung)
    seite.felder["firma"].setText("Teststudio")

    seite.speichern()

    assert einstellungen.hole(verbindung, "firma") == "Teststudio"
    assert not db.ausgabeordner().joinpath("Teststudio.pdf").exists()
    verbindung.close()


def test_und_die_seite_braucht_kein_fenster_zum_speichern(tmp_path: Path) -> None:
    """Die Seite lässt sich ohne Fenster aufbauen und speichern.

    Args:
        tmp_path: Das temporaere Verzeichnis.
    """
    verbindung = db.verbinden(tmp_path / "ohne.db")
    seite = StammdatenSeite(verbindung)

    seite.felder["firma"].setText("Tonstudio Nordwind")

    assert seite.speichern() is True
    assert einstellungen.hole(verbindung, "firma") == "Tonstudio Nordwind"
    verbindung.close()
