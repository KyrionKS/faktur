"""Die Tasten auf den Listen.

Es geht um eine Lüge, die in der Oberfläche stand und lange nicht
auffiel: Über der Taste *Neu* auf Kunden- und Leistungsliste stand ein
**⌘N**. Dieses ⌘N gehört aber dem Menü und dem Balken, und die machen
dort *ein Angebot*. Wer auf der Kundenliste ⌘N tippte, bekam ein Angebot
und keine Kundin.

Ein Kürzel, das etwas anderes tut als sein Knopf verspricht, ist
schlimmer als keines. Deshalb steht jetzt über *Neu* nichts mehr, und
über *Ändern* und *Löschen* weiterhin genau die zwei, die wirklich hier
greifen.

Und noch eine Sache: **Bei Leistungen gibt es kein *Stilllegen*.**
:func:`faktur.dateien.leistung_loeschen` nimmt nur die Verknüpfung von den
Positionen — auf alten Belegen stehen Text und Preis weiter. Es geht also
nichts verloren, und eine zweite Art, dasselbe zu tun, wäre nur ein
Umweg.
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
    from faktur import dateien

    test = Fenster(db.verbinden(tmp_path / "tasten.db"))
    dateien.kunde_speichern(test.db, {"firma": "Soundcheck GmbH"})
    dateien.leistung_speichern(
        test.db, {"bezeichnung": "Aufnahme Ton", "preis": "120,00"}
    )
    test.zeige()
    app.processEvents()  # type: ignore[attr-defined]
    return test


def _tasten(fenster: Fenster, bereich: str) -> list[str]:
    """Gibt die Aufschriften der Tasten einer Seite.

    Args:
        fenster: Das Fenster.
        bereich: Der Bereich in der Seitenleiste.

    Returns:
        Die Aufschriften in der Reihenfolge.
    """
    from PySide6.QtWidgets import QPushButton

    fenster.gehe(bereich)
    return [
        knopf.text()
        for knopf in fenster.seite().findChildren(QPushButton)
        if knopf.text()
    ]


# --------------------------------------------------------------- Die Kürzel


@pytest.mark.parametrize("bereich", ["kunden", "leistungen"])
def test_und_ueber_neu_steht_kein_kuerzel(fenster: Fenster, bereich: str) -> None:
    """⌘N ist das Angebot, nicht der Kunde und nicht die Leistung.

    Args:
        fenster: Das Fenster.
        bereich: Die Seite.
    """
    neu = [t for t in _tasten(fenster, bereich) if t.startswith("Neu")]

    assert neu == ["Neu"], f"Auf der {bereich}-Seite steht über *Neu* {neu}"


def test_und_cmd_n_macht_auch_wirklich_ein_angebot(fenster: Fenster) -> None:
    """Das Gegenstück: Das Kürzel auf dem Balken tut, was es verspricht.

    Args:
        fenster: Das Fenster.
    """
    from faktur.gui.editor import EditorFenster

    vorher = [
        w
        for w in QApplication_instanz().topLevelWidgets()
        if isinstance(w, EditorFenster)
    ]

    fenster.gehe("kunden")
    fenster.befehle.angebot.trigger()

    nachher = [
        w
        for w in QApplication_instanz().topLevelWidgets()
        if isinstance(w, EditorFenster)
    ]

    assert len(nachher) == len(vorher) + 1, "⌘N hat kein Angebot geöffnet"

    for w in nachher:
        w.close()


def QApplication_instanz() -> object:  # noqa: N802
    """Gibt die laufende Qt-Anwendung zurück.

    Returns:
        Die Anwendung.
    """
    from PySide6.QtWidgets import QApplication

    laufend = QApplication.instance()
    if laufend is None:
        raise AssertionError("Es laeuft keine Qt-Anwendung")
    return laufend


def test_und_ueber_aendern_und_loeschen_steht_ihr_kuerzel(fenster: Fenster) -> None:
    """Die zwei, die wirklich hier greifen, zeigen ihr Kürzel.

    Args:
        fenster: Das Fenster.
    """
    texte = _tasten(fenster, "kunden")

    assert any(t.startswith("Ändern") and "⌘E" in t for t in texte), (
        f"Über *Ändern* steht kein ⌘E: {texte}"
    )
    assert any(t.startswith("Löschen") and "⌫" in t for t in texte), (
        f"Über *Löschen* steht kein ⌫: {texte}"
    )


def test_und_das_kuerzel_tut_auf_der_seite_auch_das(
    fenster: Fenster, monkeypatch: pytest.MonkeyPatch
) -> None:
    """⌘E ändert den Kunden, um den es geht — nicht den der anderen Seite.

    Das Kürzel gehört dem Fenster und wirkt auf die Markierung der Seite,
    die gerade offen ist. Deshalb darf es über der Kundenliste stehen.

    **Das Blatt wird nicht abgefragt.** ``Formular.exec()`` wartet auf einen
    Klick, und im Testlauf klickt niemand — der Test bliebe hängen, bis
    das Zeitlimit die Zahl sagt, ohne zu sagen, wo es hängt. Also
    antwortet das Blatt hier mit *Abbrechen*; geprüft wird, **welches**
    Blatt es überhaupt war.

    Args:
        fenster: Das Fenster.
        monkeypatch: Zum Abfangen des Blattes.
    """
    from faktur.gui.formular import Formular

    gesehen: list[object] = []

    def abbrechen(selbst: object) -> int:
        """Merkt sich das Blatt und sagt *Abbrechen*.

        Args:
            selbst: Das Blatt.

        Returns:
            Der Rückgabewert von *Abbrechen*.
        """
        gesehen.append(selbst)
        return Formular.DialogCode.Rejected

    monkeypatch.setattr(Formular, "exec", abbrechen)

    fenster.gehe("kunden")
    seite = fenster.seite()
    seite.ansicht.setCurrentIndex(seite.modell.index(0, 0))

    fenster.befehle.aendern.trigger()

    assert len(gesehen) == 1, "⌘E hat kein Blatt geöffnet"
    assert gesehen[0].daten.get("firma") == "Soundcheck GmbH", (
        f"⌘E hat das Blatt fuer {gesehen[0].daten!r} geoeffnet"
    )


def test_und_kein_kuerzel_steht_zweimal_auf_einer_seite(fenster: Fenster) -> None:
    """Zwei Tasten mit demselben Kürzel lassen sich nicht unterscheiden.

    Args:
        fenster: Das Fenster.
    """
    for bereich in ("kunden", "leistungen"):
        texte = _tasten(fenster, bereich)
        kuerzel = [t.split()[-1] for t in texte if len(t.split()) > 1]

        assert len(kuerzel) == len(set(kuerzel)), (
            f"Auf der {bereich}-Seite steht {kuerzel} doppelt"
        )


# -------------------------------------------------------------- Stilllegen


def test_und_bei_kunden_gibt_es_stilllegen(fenster: Fenster) -> None:
    """Ein Kunde mit Belegen darf nicht verschwinden.

    Args:
        fenster: Das Fenster.
    """
    assert "Stilllegen" in _tasten(fenster, "kunden")


def test_und_bei_leistungen_gibt_es_kein_stilllegen(fenster: Fenster) -> None:
    """Bei Leistungen verschwindet nichts, wenn man sie löscht.

    Args:
        fenster: Das Fenster.
    """
    texte = _tasten(fenster, "leistungen")

    assert "Stilllegen" not in texte, f"Auf der Leistungsliste steht {texte}"
    assert [t for t in texte if t.startswith("Löschen")], (
        f"Ohne *Löschen* gäbe es gar keinen Weg mehr: {texte}"
    )


def test_und_das_gilt_auch_fuer_die_taste_daneben(fenster: Fenster) -> None:
    """Nicht nur die Taste fehlt — der Befehl auch.

    Sonst bliebe im Menü ein *Stilllegen*, das auf der Leistungsseite
    ins Leere zeigte.

    Args:
        fenster: Das Fenster.
    """
    from PySide6.QtWidgets import QPushButton

    fenster.gehe("leistungen")
    texte = [k.text() for k in fenster.seite().findChildren(QPushButton)]

    assert not [t for t in texte if "Stilllegen" in t]
