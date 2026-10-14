"""Die Werkzeuge unter `scripts/` und was sie voraussetzen.

`ablauf_pruefen.py` braucht einen Moment, das taugt nicht für den Testlauf.
Es wird von Hand gefahren und nicht von hier. Was aber in den Testlauf
gehört, ist die Voraussetzung, auf der es aufbaut:

- Es braucht die Laufzeitabhängigkeiten aus `requirements.txt`. Fehlt dort
  eine, die der Code direkt benutzt, läuft das Programm nur, weil etwas
  anderes sie zufällig mitinstalliert.
- Das Fenster muss sich ohne Bildschirm aufbauen und abzeichnen lassen.
  Sonst läuft `ablauf_pruefen.py` still vorbei, und niemand sieht es.
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path

import pytest

#: Wurzels des Projekts.
WURZEL = Path(__file__).resolve().parents[1]

#: Die Skripte, die es geben muss, und wozu.
SKRIPTE = {
    "ablauf_pruefen.py": "Durchlauf durch die ganze Oberflaeche",
    "bilder_speichern.py": "Bildschirme als PNG",
    "durchlauf_pruefen.py": "Daten anlegen und PDF schreiben, ohne Fenster",
}

#: Pakete, die direkt benutzt werden. ``pillow`` heisst in Python ``PIL``,
#: und ``PySide6-Essentials`` heisst im Code schlicht ``PySide6``.
DIREKT = {
    "PIL": "pillow",
    "reportlab": "reportlab",
    "PySide6": "PySide6-Essentials",
}


def _importe(wurzel: Path) -> set[str]:
    """Sammelt alle importierten Namen aus dem Python-Code.

    Args:
        wurzel: Der Ordner, in dem gesucht wird.

    Returns:
        Die Namen der obersten Ebenen, ohne ``faktur`` und ohne die
        Standardbibliothek.
    """
    gefunden: set[str] = set()

    for ordner in ("faktur", "scripts", "tests"):
        for datei in sorted((wurzel / ordner).rglob("*.py")):
            baum = ast.parse(datei.read_text(encoding="utf-8"))
            for knoten in ast.walk(baum):
                if isinstance(knoten, ast.Import):
                    gefunden.update(a.name.split(".")[0] for a in knoten.names)
                elif (
                    isinstance(knoten, ast.ImportFrom)
                    and knoten.level == 0
                    and knoten.module
                ):
                    gefunden.add(knoten.module.split(".")[0])

    return gefunden


def test_alle_skripte_sind_da() -> None:
    """Die Werkzeuge aus `docs/AUFBAU.md` liegen auch vor.

    Raises:
        AssertionError: Wenn eines fehlt.
    """
    fehlend = [name for name in SKRIPTE if not (WURZEL / "scripts" / name).is_file()]

    assert fehlend == [], f"Es fehlen Skripte: {fehlend}"


def test_und_die_anleitung_nennt_kein_verschwundenes_skript() -> None:
    """Kein Skript darf in `AUFBAU.md` stehen, das es nicht mehr gibt.

    `bild_pruefen.py` stand dort drei Fassungen lang, obwohl es niemand
    aufrief und es eine private Schnittstelle benutzt.

    Raises:
        AssertionError: Wenn die Anleitung etwas nennt, das fehlt.
    """
    text = (WURZEL / "docs" / "AUFBAU.md").read_text(encoding="utf-8")

    genannt = set(re.findall(r"scripts/([a-z_]+\.py)", text))
    vorhanden = {name for name in SKRIPTE}

    assert genannt <= vorhanden, (
        f"`AUFBAU.md` nennt Skripte, die es nicht gibt: {sorted(genannt - vorhanden)}"
    )


def test_das_fenster_laesst_sich_ohne_bildschirm_zeichnen(tmp_path: Path) -> None:
    """Das Fenster baut sich auf und liefert ein Bild.

    `bilder_speichern.py` und `ablauf_pruefen.py` zeichnen das Fenster mit
    ``grab()``. Bricht das, gehen beide Skripte still vorbei, weil sie
    nicht im Testlauf stehen.

    Args:
        tmp_path: Das Verzeichnis fuer die Datenbank. **Nicht** im Projekt:
            eine Datenbankdatei im Repository ist ein Fehler, und
            `tests/test_repository.py` schlaegt sofort an.
    """
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

    from faktur import db
    from faktur.gui.fenster import Fenster
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])
    fenster = Fenster(db.verbinden(tmp_path / "probelauf.db"))
    fenster.zeige()

    try:
        bild = fenster.fenster.grab()
        assert not bild.isNull(), "Das Fenster liefert kein Bild."
        assert bild.width() > 0, "Das Bild hat keine Breite."
    finally:
        fenster.fenster.close()


def test_keine_bibliothek_die_nur_zufaellig_dabei_war() -> None:
    """Nur die schlanken Qt-Teile, nicht das ganze Paket.

    ``PySide6`` ohne ``-Essentials`` bringt WebEngine, Qt3D und den
    Designer mit — gemessen 676 MB statt 248 MB auf Linux aarch64 mit
    6.12.0. Kein Fenster von Faktur braucht davon etwas.

    Raises:
        AssertionError: Wenn das volle Paket verlangt wird.
    """
    liste = (WURZEL / "requirements.txt").read_text(encoding="utf-8")

    gepinnt = re.findall(r"^([A-Za-z0-9._-]+)==", liste, re.M)
    qt = [paket for paket in gepinnt if paket.lower().startswith("pyside6")]

    assert qt == ["PySide6-Essentials"], (
        f"In `requirements.txt` steht {qt}. Gewollt ist `PySide6-Essentials` — "
        "das volle Paket ist rund 428 MB größer und bringt Addons mit, die "
        "hier nicht vorkommen."
    )


def test_jede_bibliothek_steht_in_der_liste() -> None:
    """Was der Code direkt benutzt, steht auch in `requirements.txt`.

    `rich` wurde dreimal direkt importiert und stand in keiner Liste. Es
    lief nur, weil Textual es zufällig mitinstalliert — ohne das hätte der
    erste, der Textual aufrüstet, ein `ModuleNotFoundError` bekommen.

    Raises:
        AssertionError: Wenn eine direkt benutzte Bibliothek fehlt.
    """
    liste = (WURZEL / "requirements.txt").read_text(encoding="utf-8")
    gefunden = re.findall(r"^([A-Za-z0-9._-]+)==", liste, re.M)
    gepinnt = {paket.lower() for paket in gefunden}

    importierte = _importe(WURZEL)
    # Beide Seiten in Kleinbuchstaben: ``PySide6-Essentials`` steht in der
    # Liste gross, der Code schreibt ``PySide6``.
    benutzt = {paket.lower() for modul, paket in DIREKT.items() if modul in importierte}
    fehlend = sorted(benutzt - gepinnt)

    assert fehlend == [], (
        f"Diese Bibliotheken werden direkt benutzt, stehen aber nicht in "
        f"`requirements.txt`: {fehlend}"
    )


@pytest.mark.parametrize("name", sorted(SKRIPTE))
def test_die_skripte_sind_gueltiges_python(name: str) -> None:
    """Jedes Skript lässt sich zumindest lesen.

    Args:
        name: Der Dateiname im Ordner `scripts`.
    """
    quelle = (WURZEL / "scripts" / name).read_text(encoding="utf-8")

    ast.parse(quelle), f"{name} ist kein gültiges Python."
