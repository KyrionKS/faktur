"""Der Start des Programms.

Bis hierher lief kein Test, der ``main()`` wirklich aufruft. Alle anderen
rufen die Klassen direkt auf — und so kam ein Aufruf zustande, den noch
niemand ausgeführt hatte: Das Fenster wurde mit ``show()`` geöffnet,
obwohl die Methode ``zeige()`` heißt. Der Traceback auf dem Mac sagte es
in zwei Zeilen.

Darum steht hier nicht irgendein Test, sondern **genau der Aufruf, den ein
Benutzer macht**: ``python -m faktur``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

from faktur import db  # noqa: E402
from faktur.gui import app  # noqa: E402

#: Wo die Oberflaege liegt.
GUI = Path(__file__).resolve().parents[1] / "faktur" / "gui"


@pytest.fixture
def frisch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Legt eine frische Datenbank bereit.

    Args:
        monkeypatch: Zum Umleiten der Datenbank.
        tmp_path: Das Verzeichnis fuer die Datei.

    Returns:
        Der Pfad zur Datenbank.
    """
    ziel = tmp_path / "start.db"
    monkeypatch.setattr(app, "_verbindung", lambda: db.verbinden(ziel))
    monkeypatch.setattr(app, "_bild", lambda: None)
    return ziel


def test_der_start_zeigt_ein_fenster(frisch: Path) -> None:
    """``python -m faktur`` öffnet ein Fenster und beendet sich wieder.

    Der Timer stellt die Schleife ab, so wie ein Benutzer es mit Cmd+Q
    täte. Ohne ihn endet ``app.exec()`` nie.

    Args:
        frisch: Die frische Datenbank.
    """
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    laufend = QApplication.instance() or QApplication([])
    QTimer.singleShot(0, laufend.quit)

    ergebnis = app.main(["faktur"])

    assert ergebnis == 0, "Der Start meldet einen Fehler."


def test_und_das_fenster_ist_auch_wirklich_offen(frisch: Path) -> None:
    """Nach dem Start steht ein sichtbares Fenster da.

    Args:
        frisch: Die frische Datenbank.
    """
    from faktur.gui.fenster import BEREICHE, Fenster
    from PySide6.QtWidgets import QApplication

    laufend = QApplication.instance() or QApplication([])
    fenster = Fenster(app._verbindung())
    fenster.zeige()
    laufend.processEvents()

    sichtbar = fenster.fenster.isVisible()
    breite = fenster.fenster.width()
    bereiche = len(BEREICHE)

    fenster.fenster.close()

    assert sichtbar, "Das Fenster ist offen, aber nicht zu sehen."
    assert breite > 400, f"Das Fenster ist {breite} Pixel breit."
    erwartet = [
        "Übersicht",
        "Projekte",
        "Dokumente",
        "Offene Forderungen",
        "Kunden",
        "Leistungen",
        "Stammdaten",
    ]
    assert bereiche == len(erwartet), (
        f"Die Seitenleiste hat {bereiche} Bereiche, erwartet werden {len(erwartet)}."
    )
    for nummer, (_schluessel, titel, _kuerzel) in enumerate(BEREICHE):
        assert titel == erwartet[nummer], (
            f"Auf Platz {nummer + 1} steht „{titel}“, erwartet wird "
            f"„{erwartet[nummer]}“."
        )


def test_jeder_aufruf_auf_dem_fenster_gibt_es_auch() -> None:
    """Kein Aufruf, den es auf dem Fenster nicht gibt.

    Genau daran ist 0.10 auf dem Mac gescheitert: ``fenster.show()`` neben
    einem Objekt, das nur ``zeige()`` kennt. Diese Prüfung findet solche
    Stellen an einer Stelle, statt sie beim nächsten Start zu entdecken.

    Args:
        None
    """
    from faktur.gui.fenster import Fenster

    quelle = (GUI / "app.py").read_text(encoding="utf-8")
    gefunden: list[str] = []

    for nummer, zeile in enumerate(quelle.splitlines(), start=1):
        vor, _, nach = zeile.partition("fenster.")
        if not nach or vor.lstrip().startswith("#"):
            continue
        name = nach.split("(")[0].strip()
        if not name or not name.isidentifier():
            continue
        gefunden.append(name)
        assert hasattr(Fenster, name), (
            f"app.py:{nummer} ruft fenster.{name}() auf — Fenster kann das nicht."
        )

    assert gefunden, "In app.py wird gar nichts am Fenster aufgerufen."


def test_und_ohne_pyside6_gibt_es_einen_satz_statt_eines_stapels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fehlt die Bibliothek, gibt es eine Zeile für die Konsole.

    Args:
        monkeypatch: Zum Verbergen von PySide6.
    """
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", None)

    assert app.main(["faktur"]) == 1


def test_und_der_einstiegspunkt_sagt_die_echte_version() -> None:
    """``python -m faktur --version`` nennt die Version aus dem Paket.

    Als Unterprozess, weil es ein Unterprozess ist, den man aufruft.

    Args:
        None
    """
    import subprocess

    from faktur import __version__

    ergebnis = subprocess.run(
        [sys.executable, "-m", "faktur", "--version"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
        timeout=120,
        check=False,
    )

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert ergebnis.stdout.strip() == f"Faktur {__version__}"
