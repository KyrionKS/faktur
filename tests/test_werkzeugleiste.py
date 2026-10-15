"""Der Balken über dem Fenster.

Velox hat einen, und er ist der schnellste Weg zu den Dingen, die man am
häufigsten braucht. Faktur jetzt auch — mit einer Bedingung, die in Velox
nicht nötig war und hier doch:

**Menü und Balken müssen dieselbe Aktion teilen.** Zwei eigene Aktionen
mit demselben Kürzel quittiert Qt nur mit einer Warnung, und danach feuert
das Kürzel manchmal zweimal. Diese Datei prüft darum nicht nur, *dass*
etwas da ist, sondern dass es *einmal* da ist.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

from faktur import db  # noqa: E402
from faktur.gui.fenster import Fenster  # noqa: E402


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
    """Baut ein Fenster mit frischer Datenbank.

    Returns:
        Das Fenster.
    """
    test = Fenster(db.verbinden(tmp_path / "werkzeug.db"))
    test.zeige()
    app.processEvents()  # type: ignore[attr-defined]
    return test


def _ohne_trenner(aktionen: object) -> list[object]:
    """Filtert die Trenner aus einer Liste von Aktionen.

    Args:
        aktionen: Die Aktionen, etwa ``balken.actions()``.

    Returns:
        Die Aktionen, die keine Trenner sind.
    """
    return [
        a
        for a in aktionen
        if not a.isSeparator() and a.text()  # type: ignore[attr-defined]
    ]


def _datei_aktionen(fenster: Fenster) -> list[object]:
    """Gibt die Aktionen aus dem Menü *Datei*.

    Args:
        fenster: Das Fenster.

    Returns:
        Die Aktionen ohne die Trenner.
    """
    return _ohne_trenner(fenster.fenster.menuBar().actions()[0].menu().actions())


def _offene_editoren() -> list[object]:
    """Gibt alle offenen Dokumentfenster zurück.

    Returns:
        Die Fenster.
    """
    from faktur.gui.editor import EditorFenster
    from PySide6.QtWidgets import QApplication

    laufend = QApplication.instance()
    if laufend is None:
        return []
    return [w for w in laufend.topLevelWidgets() if isinstance(w, EditorFenster)]


# ---------------------------------------------------------------- Der Balken


def test_es_gibt_einen_balken(fenster: Fenster) -> None:
    """Über dem Fenster liegt eine Leiste.

    Args:
        fenster: Das Fenster.
    """
    assert fenster.fenster.findChildren(type(fenster.werkzeug)), (
        "Der Balken haengt nicht am Fenster."
    )


def test_und_er_hat_die_haeufigsten_befehle(fenster: Fenster) -> None:
    """Kunde, Angebot, Abrechnen — und rechts der Export.

    Args:
        fenster: Das Fenster.
    """
    texte = [a.text() for a in _ohne_trenner(fenster.werkzeug.actions())]

    assert texte == [
        "Neuer Kunde",
        "Neues Angebot",
        "Aus Angebot abrechnen",
        "Exportieren…",
    ], f"Auf dem Balken steht {texte}"


def test_und_er_ist_nicht_verschiebbar(fenster: Fenster) -> None:
    """Ein Balken, den man herumschiebt, steht danach woanders.

    Args:
        fenster: Das Fenster.
    """
    assert fenster.werkzeug.isMovable() is False
    assert fenster.werkzeug.isFloatable() is False


def test_und_auf_dem_mac_ist_er_teil_der_titelleiste(
    app: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ohne das steht ein zweiter Streifen unter dem Titel.

    Geprüft wird der **Aufruf**, nicht der Zustand: Qt setzt den Zustand
    nur auf dem Mac — unter Linux liefert der Getter immer ``False``, egal
    was man ihm vorher gegeben hat. Ein Test auf den Getter wäre hier
    grün oder rot, ohne dass irgendetwas über den Mac gesagt wäre.

    Args:
        app: Die Qt-Anwendung.
        tmp_path: Das temporäre Verzeichnis.
        monkeypatch: Zum Aufzeichnen des Aufrufs.
    """
    del tmp_path
    del app
    from PySide6 import QtWidgets

    gerufen: list[bool] = []
    echtes_setzen = QtWidgets.QMainWindow.setUnifiedTitleAndToolBarOnMac

    def tu_setzen(self: object, an: bool) -> None:
        """Merkt sich, dass es aufgerufen wurde.

        Args:
            self: Das Fenster.
            an: Ob der Balken mit der Titelleiste vereint wird.

        Returns:
            Nichts.
        """
        gerufen.append(an)
        echtes_setzen(self, an)

    monkeypatch.setattr(
        QtWidgets.QMainWindow, "setUnifiedTitleAndToolBarOnMac", tu_setzen
    )

    Fenster(db.verbinden(Path("/tmp") / "titelleiste.db"))

    assert gerufen == [True], (
        f"setUnifiedTitleAndToolBarOnMac wurde {len(gerufen)}-mal aufgerufen, "
        "einmal mit True waere richtig."
    )


def test_und_jeder_strich_hat_ein_bild(fenster: Fenster) -> None:
    """Eine Taste ohne Bild ist auf dem Balken nur ein Wort.

    Args:
        fenster: Das Fenster.
    """
    ohne = [
        a.text() for a in _ohne_trenner(fenster.werkzeug.actions()) if a.icon().isNull()
    ]

    assert ohne == [], f"Ohne Bild: {ohne}"


def test_und_die_zwei_gezeichneten_bilder_sind_verschieden(
    fenster: Fenster,
) -> None:
    """Kunde und Angebot duerfen nicht dasselbe Bild tragen.

    Args:
        fenster: Das Fenster.
    """
    kunde = fenster.befehle.kunde.icon().pixmap(32, 32)
    angebot = fenster.befehle.angebot.icon().pixmap(32, 32)

    assert not kunde.isNull(), "Das Kundenbild ist leer"
    assert not angebot.isNull(), "Das Angebotsbild ist leer"
    assert kunde.toImage() != angebot.toImage(), (
        "Kunde und Angebot tragen dasselbe Bild — auf dem Balken sind sie "
        "nicht auseinanderzuhalten."
    )


def test_und_der_hinweis_steht_an_jeder_taste(fenster: Fenster) -> None:
    """Wer mit der Maus auf dem Balken steht, soll etwas erfahren.

    Args:
        fenster: Das Fenster.
    """
    ohne = [
        a.text() for a in _ohne_trenner(fenster.werkzeug.actions()) if not a.toolTip()
    ]

    assert ohne == [], f"Ohne Hinweis: {ohne}"


# ------------------------------------------------- Einmal, nicht zweimal


def test_menue_und_balken_teilen_sich_die_aktionen(fenster: Fenster) -> None:
    """Der Balken zeigt dieselben Objekte wie das Menü.

    Args:
        fenster: Das Fenster.
    """
    im_menue = {id(a): a for a in _datei_aktionen(fenster)}
    im_balken = {id(a): a for a in _ohne_trenner(fenster.werkzeug.actions())}

    geteilt = set(im_menue) & set(im_balken)

    assert geteilt, "Menü und Balken teilen sich keine einzige Aktion"
    for nummer in geteilt:
        assert im_menue[nummer] is im_balken[nummer]


def test_und_kein_befehl_steht_doppelt_auf_dem_balken(
    fenster: Fenster,
) -> None:
    """Zweimal derselbe Befehl auf dem Balken sieht nach einem Fehler aus.

    Args:
        fenster: Das Fenster.
    """
    texte = [a.text() for a in _ohne_trenner(fenster.werkzeug.actions())]

    assert len(texte) == len(set(texte)), f"Auf dem Balken steht {texte} doppelt"


def test_und_kein_kuerzel_fehrt_zweimal(fenster: Fenster) -> None:
    """Zwei Aktionen mit demselben Kürzel lassen sich nicht unterscheiden.

    Qt warnt, tut aber sonst nichts — und dann feuert das Kürzel
    manchmal zweimal.

    Args:
        fenster: Das Fenster.
    """
    kuerzel: dict[str, list[str]] = {}
    for aktion in fenster.fenster.actions():
        if aktion.isSeparator():
            continue
        text = aktion.shortcut().toString()
        if text:
            kuerzel.setdefault(text, []).append(aktion.text())

    doppelt = {k: v for k, v in kuerzel.items() if len(v) > 1}

    assert doppelt == {}, f"Diese Kürzel hängen an mehreren Befehlen: {doppelt}"


def test_und_das_menue_haelt_alles_was_der_balken_zeigt(
    fenster: Fenster,
) -> None:
    """Was auf dem Balken steht, steht auch im Menü — und umgekehrt nicht.

    Args:
        fenster: Das Fenster.
    """
    im_balken = {a.text() for a in _ohne_trenner(fenster.werkzeug.actions())}
    im_menue = {a.text() for a in _datei_aktionen(fenster)}

    assert im_balken <= im_menue, (
        f"Auf dem Balken steht, was im Menü fehlt: {im_balken - im_menue}"
    )


def test_und_die_nur_im_menue_stehen_dort_auch(fenster: Fenster) -> None:
    """Suchen und Öffnen gehören nicht auf den Balken.

    Beim Suchen ist die Seite entscheidend, nicht das Fenster — es gibt
    einen Suchraum, keinen Suchknopf. Und *Öffnen* ist eine Handlung an
    der markierten Zeile.

    Args:
        fenster: Das Fenster.
    """
    im_balken = {a.text() for a in _ohne_trenner(fenster.werkzeug.actions())}

    assert "Suchen" not in im_balken
    assert "Dokument öffnen" not in im_balken
    assert "Ändern" not in im_balken


# --------------------------------------------------------- Sie tun auch was


def test_und_neues_angebot_oeffnet_ein_fenster(fenster: Fenster) -> None:
    """Der Klick auf dem Balken macht, was der Text sagt.

    Args:
        fenster: Das Fenster.
    """
    vorher = len(_offene_editoren())

    fenster.befehle.angebot.trigger()

    assert len(_offene_editoren()) == vorher + 1, (
        "Der Klick auf *Neues Angebot* hat kein Fenster geöffnet."
    )


def test_und_exportieren_sagt_dass_es_noch_nicht_da_ist(fenster: Fenster) -> None:
    """Der Export kommt als nächstes. Bis dahin sagt Faktur das auch.

    Stille Knöpfe sind schlimmer als keine.

    Args:
        fenster: Das Fenster.
    """
    fenster.befehle.exportieren.trigger()

    nachricht = fenster.fenster.statusBar().currentMessage()
    assert "Export" in nachricht, f"Die Statuszeile sagt nur „{nachricht}“"
